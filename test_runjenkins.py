import unittest
from unittest.mock import MagicMock

import click
from click.testing import CliRunner

import runjenkins


class TestRunJenkins(unittest.TestCase):
    def test__runbuild(self):
        # Test Data
        job_name = "testjob"
        params = {"key": "value"}
        nbn = 10

        # Mocks
        server = MagicMock()
        server.get_job_info = MagicMock(return_value={'nextBuildNumber': nbn})
        server.build_job = MagicMock()
        server.get_build_info = MagicMock(
            return_value={'building': False,
                          'result': "SUCCESS",
                          'url': "http://buildurl.com"})

        # Execute function under test
        runjenkins._runbuild(job_name, params, server)

        # Check mock objects for calls
        server.get_job_info.assert_called_with(job_name)
        server.build_job.assert_called_with(job_name, params)
        server.get_build_info(job_name, nbn)


def test_hello_world():
    @click.command()
    @click.argument('name')
    def hello(name):
        click.echo('Hello %s!' % name)

    runner = CliRunner()
    result = runner.invoke(hello, ['Peter'])
    assert result.exit_code == 0
    assert result.output == 'Hello Peter!\n'
