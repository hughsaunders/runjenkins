|Build Status|

runjenkins
==========

Simple tool for running a list of jenkins jobs

Tool for running jenkins jobs from cli, based on yaml configs. The ideas
is that you have a single creds file, then put a config file in each
repo/workspace. Then add it to your commit
hook/alias/function/script/whatever so that you can run jobs on commit.

I know the obvious way to run jobs on commit is to open a PR, and use
branch source or GHPRB. However when developing JJB jobs, I often want
to run a job that runs JJB, then the job that was created, and possibly
some other test jobs. This tool lets me automate that.

Example Creds File:
-------------------

::

    ---
     url:  https://myjenkins.example.com/
     user: foo
     password: bah

Example Conf File:
------------------

::

    ---
    - myjob:
        myparamkey: myparamvalue
    - mynextjob:
        parama: 1
        paramb: false
    - parallel group: # <-- name arbitrary, parallel detected by val=list
                            rather than dict
      - myparalleljob:
          param: val
      - otherparalleljob:
          param: val

.. |Build Status| image:: https://travis-ci.org/hughsaunders/runjenkins.svg?branch=master
   :target: https://travis-ci.org/hughsaunders/runjenkins
