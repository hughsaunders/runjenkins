#!/usr/bin/env python3

import logging
import os
import threading
import time
import webbrowser

import click
import jenkins
import yaml


# Tool for running jenkins jobs from cli, based on yaml configs.
# The ideas is that you have a single creds file, then put a config
# file in each repo/workspace. Then add it to your commit.
# hook/alias/function/script/whatever so that you can run jobs on commit.

# I know the obvious way to run jobs on commit is to open a PR, and use
# branch source or GHPRB. However when developing JJB jobs, I often want
# to run a job that runs JJB, then the job that was created.

# Creds:
# ---
#  url:  https://myjenkins.example.com/
#  user: foo
#  password: bah

# Conf:
# ---
# - myjob:
#     myparamkey: myparamvalue
# - mynextjob:
#     parama: 1
#     paramb: false
# - parallel group: # <-- name arbitrary, parallel detected by val=list
#                         rather than dict
#   - myparalleljob:
#       param: val
#   - otherparalleljob:
#       param: val


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


def _runbuild(job_name, params, server):
    # This is very racy. jenkins.Jenkins.build_job should return
    # something useful so we don't have to guess the build number
    logger.debug("Run Build: {jn}, {p}".format(jn=job_name, p=params))
    l = threading.local()
    l.current_thread = threading.current_thread()
    l.prog_marker = "[{}]".format(l.current_thread.getName())
    # when not running in parallel, use a shorter progress marker
    if l.prog_marker == "[MainThread]":
        l.prog_marker = "."
    l.nbn = server.get_job_info(job_name)['nextBuildNumber']
    server.build_job(job_name, params)
    l.print_info = True
    while True:
        try:
            l.build_info = server.get_build_info(job_name, l.nbn)
            # get_build_info may fail, print info once after
            # it succeeds.
            if l.print_info:
                print ("Started build, job_name: {jn},"
                       " params: {p}, url: {u}"
                       .format(jn=job_name,
                               p=params,
                               u=l.build_info['url']))
                l.print_info = False
            if l.build_info['building'] is False:
                l.result = l.build_info['result']
                print("{jn} complete, result:{r}".format(
                    jn=job_name, r=l.build_info['result']))
                if l.result != "SUCCESS":
                    webbrowser.open(l.build_info['url'])
                    raise BuildFailureException(
                        "Job {jn} failed :(".format(jn=job_name))
                break
        except (jenkins.NotFoundException,
                jenkins.JenkinsException):
            print("x", end="")
        else:
            print(l.prog_marker, end= "")
        time.sleep(15)


@cli.command()
def runbuild():
    """Run predefined builds."""
    context = click.get_current_context()
    obj = context.obj
    try:
        # Check all the requested jobs exist before starting
        # jobs = obj.server.get_jobs()
        # server_job_names = [j['name'] for j in jobs]
        # config_job_names = [list(c.keys())[0] for c in obj.conf]
        # if not all(cjn in server_job_names for cjn in config_job_names):
        #     print ""

        # Checking all jobs exist initially isn't a good idea as
        # some jobs may be created by earlier jobs (eg when using JJB)

        for jobdict in obj.conf:
                job_name = list(jobdict.keys())[0]
                params = jobdict[job_name]
                if type(params) == dict:
                    # serial build
                    _runbuild(job_name, params, obj.server)
                elif type(params) == list:
                    # parallel

                    p_jobs = params
                    logger.debug("Found parallel block {}".format(p_jobs))

                    # Track threads in this list
                    threads = []

                    # Create and start a thread per job
                    for p_jobdict in p_jobs:
                        job_name = list(p_jobdict.keys())[0]
                        params = p_jobdict[job_name]
                        job_thread = threading.Thread(target=_runbuild,
                                                      args=(job_name, params,
                                                            obj.server))
                        threads.append(job_thread)
                        job_thread.setName(job_name)
                        job_thread.start()

                    # Wait for every thread to finish before continuing
                    for t in threads:
                        t.join()
                else:
                    raise ValueError("Invalid runjenkins conf")

    except BuildFailureException as e:
        print(e)
        context.exit(1)

if __name__ == "__main__":
    cli()
