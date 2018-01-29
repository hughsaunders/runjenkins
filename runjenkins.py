#!/usr/bin/env python3

import logging
import os
import queue
import threading
import time
import urllib
import webbrowser

import click
import jenkins
import yaml


class Obj(object):
    pass


class BuildFailureException(Exception):
    pass


logger = logging.getLogger()


@click.group()
@click.option('--credsfile', default="~/.runjenkinscreds.yml")
@click.option('--conffile', default="./runjenkins.yml")
@click.option('--debug/--no-debug', default=False)
def cli(credsfile, conffile, debug):
    if debug:
        logger.setLevel(logging.DEBUG)
    logger.debug("RunJenkins")
    context = click.get_current_context()
    context.obj = Obj()
    obj = context.obj
    obj.creds = yaml.load(open(os.path.expanduser(credsfile), 'r'))
    obj.conf = yaml.load(open(conffile, 'r'))
    logging.debug("Config: {}".format(obj.conf))
    obj.server = jenkins.Jenkins(obj.creds['url'],
                                 username=obj.creds['user'],
                                 password=obj.creds['password'])
    logger.debug("Connection Established")


def _runbuild(job_name, params, server, poll_interval=15,
              results=queue.Queue()):
    """Start a build, poll until it exits."""
    # This function should be threadsafe, its run by threading.Thread

    try:

        logger.debug("Run Build: {jn}, {p}".format(jn=job_name, p=params))

        # To avoid thread conflicts, locals should be stored on the
        # lo object
        lo = threading.local()
        lo.current_thread = threading.current_thread()

        # Set thread name to job name to make it easy to determine which
        # job/thread an exception ocurred in.
        lo.current_thread.setName(job_name)

        # pick a lower case letter to identify this thread, used when printing
        # progress markers
        lo.prog_marker = chr(((lo.current_thread.ident % 26) + 97))

        # This is very racy. jenkins.Jenkins.build_job should return
        # something useful so we don't have to guess the build number
        lo.nbn = server.get_job_info(job_name)['nextBuildNumber']
        server.build_job(job_name, params)
        lo.print_info = True
        while True:
            try:
                lo.build_info = server.get_build_info(job_name, lo.nbn)
                # get_build_info may fail, print info once after
                # it succeeds.
                if lo.print_info:
                    print("Started build, job_name: {jn},"
                          " params: {p}, url: {u}, progress marker: {pm}"
                          .format(jn=job_name,
                                  p=params,
                                  u=lo.build_info['url'],
                                  pm=lo.prog_marker),
                          flush=True)
                    lo.print_info = False
                    # avoid printing progress marker after initial job info
                    continue
                if lo.build_info['building'] is False:
                    lo.result = lo.build_info['result']
                    print("{jn} complete, result:{r}".format(
                        jn=job_name, r=lo.build_info['result']), flush=True)
                    if lo.result != "SUCCESS":
                        webbrowser.open(lo.build_info['url'])
                        results.put(False)
                        raise BuildFailureException(
                            "Job {jn} failed :(".format(jn=job_name))
                    results.put(True)
                    break
            except (jenkins.NotFoundException,
                    jenkins.JenkinsException,
                    urllib.error.HTTPError):
                # print an exception marker for any exceptions after the
                # initial queuing period.
                if not lo.print_info:
                    print("{pm}-x".format(pm=lo.prog_marker), end=" ",
                          flush=True)
                else:
                    # Reduce polling interval while waiting for build to start
                    time.sleep(1)
                    continue
            else:
                # print a progress marker
                print(lo.prog_marker, sep=" ", end=" ", flush=True)
            time.sleep(poll_interval)
    except Exception as e:
        results.put(False)
        raise e


def _check_jobs_exist():
    context = click.get_current_context()
    obj = context.obj
    # Check all the requested jobs exist before starting
    logger.debug("Checking jobs exist before starting builds")
    jobs = obj.server.get_jobs()
    server_job_names = [j['name'] for j in jobs]
    config_job_names = []
    for item in obj.conf:
        key = list(item.keys())[0]
        value = item[key]
        if type(value) == dict:
            config_job_names.append(key)
        elif type(value) == list:
            for i in value:
                name = next(iter(i))
                config_job_names.append(name)

    missing_jobs = set(config_job_names) - set(server_job_names)
    if missing_jobs:
        print("The following jobs are in runjenkins config but arent"
              " defined on the jenkins master: {}".format(missing_jobs))
        context.exit(1)


def _run_parallel(params, poll_interval):
    context = click.get_current_context()
    obj = context.obj
    # Parallel builds are executed in one thread per
    # build. Exceptions can't be caught across threads
    # so a queue is used to communicate the result back
    # to the main thread.

    p_jobs = params
    logger.debug("Found parallel block {}".format(p_jobs))

    # Track threads in this list
    threads = []
    # Track results in a threadsafe queue
    results = queue.Queue()

    # Create and start a thread per job
    for p_jobdict in p_jobs:
        job_name = list(p_jobdict.keys())[0]
        params = p_jobdict[job_name]
        job_thread = threading.Thread(target=_runbuild,
                                      args=(job_name, params,
                                            obj.server,
                                            poll_interval,
                                            results))
        threads.append(job_thread)
        job_thread.start()

    # Wait for every thread to finish before continuing
    for t in threads:
        # join with a short timeout so the main thread
        # can be interrupted regularly (eg by ctrl-c)
        while True:
            t.join(1)
            if not t.isAlive():
                break
    # Set return code if there was at least one failure
    # Stack trace will have already been printed
    while not results.empty():
        if not results.get():
            context.exit(1)


@cli.command()
@click.option("--poll-interval", default=15,
              help="How often to poll for build status in seconds.")
@click.option("--check-jobs-exist/--no-check-jobs-exist", default=False,
              help="When enabled, runjenkins will ensure all jobs referenced"
              "by the config exist before starting the first build.")
def runbuild(poll_interval, check_jobs_exist):
    """Run predefined builds."""
    context = click.get_current_context()
    obj = context.obj

    if check_jobs_exist:
        _check_jobs_exist()

    for jobdict in obj.conf:
        job_name = list(jobdict.keys())[0]
        params = jobdict[job_name]
        if type(params) == dict:
            # serial build, executed in the main thread,
            # so exceptions can be caught normally.
            try:
                _runbuild(job_name, params, obj.server)
            except BuildFailureException as e:
                print(e)
                context.exit(1)
        elif type(params) == list:
            _run_parallel(params, poll_interval)
        else:
            raise ValueError("Invalid runjenkins conf")


if __name__ == "__main__":
    cli()
