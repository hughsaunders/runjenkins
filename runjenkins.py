#!/usr/bin/env python

import os
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


class Obj(object):
    pass


class BuildFailureException(Exception):
    pass


@click.group()
@click.option('--credsfile', default="~/.runjenkinscreds.yml")
@click.option('--conffile', default="./runjenkins.yml")
def cli(credsfile, conffile):
    context = click.get_current_context()
    context.obj = Obj()
    obj = context.obj
    obj.creds = yaml.load(open(os.path.expanduser(credsfile), 'r'))
    obj.conf = yaml.load(open(conffile, 'r'))
    obj.server = jenkins.Jenkins(obj.creds['url'],
                                 username=obj.creds['user'],
                                 password=obj.creds['password'])


@cli.command()
def runbuild():
    """Run predefined builds in serial."""
    context = click.get_current_context()
    obj = context.obj
    try:
        for jobdict in obj.conf:
                job_name = jobdict.keys()[0]
                params = jobdict[job_name]
                # This is very racy. jenkins.Jenkins.build_job should return
                # something useful so we don't have to guess the build number
                nbn = obj.server.get_job_info(job_name)['nextBuildNumber']
                obj.server.build_job(job_name, params)
                print_info = True
                while True:
                    try:
                        build_info = obj.server.get_build_info(job_name, nbn)
                        # get_build_info may fail, print info once after
                        # it succeeds.
                        if print_info:
                            print ("Started build, job_name: {jn},"
                                   " params: {p}, url: {u}"
                                   .format(jn=job_name,
                                           p=params,
                                           u=build_info['url']))
                            print_info = False
                        if build_info['building'] is False:
                            result = build_info['result']
                            print "{jn} complete, result:{r}".format(
                                jn=job_name, r=build_info['result'])
                            if result != "SUCCESS":
                                webbrowser.open(build_info['url'])
                                raise BuildFailureException(
                                    "Job {jn} failed :(".format(jn=job_name))
                            break
                    except (jenkins.NotFoundException,
                            jenkins.JenkinsException):
                        print "x",
                    else:
                        print ".",
                    time.sleep(15)
    except BuildFailureException as e:
        print e
        context.exit(1)


cli()
