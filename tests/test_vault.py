#!/usr/bin/env python3

import os
import subprocess
from shutil import copyfile
from pathlib import Path, PosixPath

import pytest

import src.vault as vault


CONTENT_TEST_YAML = Path("./tests/data/test.yaml")
CONTENT_TEST_YAML_DEC = Path("./tests/data/test.yaml.dec")


@pytest.fixture
def tmp_path_data(tmp_path) -> PosixPath:
    copyfile(
        CONTENT_TEST_YAML, tmp_path.joinpath(CONTENT_TEST_YAML.name))
    copyfile(
        CONTENT_TEST_YAML_DEC, tmp_path.joinpath(CONTENT_TEST_YAML_DEC.name))
    return tmp_path


def test_load_yaml(tmp_path_data: PosixPath):
    parsed = vault.parse_args()
    obj = vault.HelmVault(
        *parsed.parse_known_args([
            "enc", "-f", str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name))
        ])
    )
    data = obj._load_yaml()
    assert isinstance(data, dict)


def test_parser(tmp_path_data: PosixPath):
    parsed = vault.parse_args()
    parser = parsed.parse_known_args([
        "clean",
        "-f",
        str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name))
    ])
    assert(parser)


def filecheckfunc():
    raise FileNotFoundError


def test_enc(tmp_path_data: PosixPath, capsys):
    input_values = ["adfs1", "adfs2", "adfs3", "adfs4"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input

    vault.main(["enc", str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name))])

    output.append(capsys.readouterr().out)

    assert output == [
        'Input a value for nextcloud.password: ',
        'Input a value for /secret/testdata.user: ',
        'Input a value for /secret/testdata.password: ',
        'Input a value for mariadb/db.password: ',
        'Done Encription\n',
    ]


def test_enc_with_env(tmp_path_data: PosixPath, capsys):
    os.environ["HELM_VAULT_KVVERSION"] = "v2"
    input_values = ["adfs1", "adfs2", "adfs3", "adfs4"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input

    vault.main([
        'enc',
        str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name)),
        '-e',
        'test'
    ])

    output.append(capsys.readouterr().out)

    assert output == [
        'Input a value for nextcloud.password: ',
        'Input a value for /secret/testdata.user: ',
        'Input a value for /secret/test/testdata.password: ',
        'Input a value for mariadb/db.password: ',
        'Done Encription\n',
    ]


def test_refuse_enc_from_file_with_bad_name():
    with pytest.raises(Exception) as e:
        vault.main([
            'enc',
            str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name)),
            '-s',
            './tests/test.yaml.bad'
        ])
        assert "ERROR: Secret file name must end with" in str(e.value)


def test_dec(tmp_path_data: PosixPath, capsys):
    input_values = ["adfs1", "adfs2"]
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input

    vault.main(['dec', str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name))])
    output.append(capsys.readouterr().out)

    assert output == [
        'Done Decrypting\n',
    ]


def test_clean_dec_not_exist(tmp_path: PosixPath):
    with pytest.raises(FileNotFoundError):
        vault.main([
            "clean",
            "-v",
            "-f",
            str(tmp_path.joinpath("test-not-exist.yaml"))
        ])


def test_clean(tmp_path_data: PosixPath):
    vault.main([
        "clean",
        "-v",
        "-f",
        str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name))
    ])


@pytest.mark.skipif(
    subprocess.run("helm", shell=True),
    reason="No way of testing without Helm"
)
def test_install(tmp_path_data: PosixPath):
    os.environ["HELM_VAULT_KVVERSION"] = "v2"
    input_values = []
    output = []

    def mock_input(s):
        output.append(s)
        return input_values.pop(0)
    vault.input = mock_input
    vault.print = lambda s: output.append(s)

    vault.main([
        'install',
        "stable/nextcloud",
        "--name",
        "nextcloud",
        "--namespace",
        "nextcloud",
        "-f",
        str(tmp_path_data.joinpath(CONTENT_TEST_YAML.name)),
        "--dry-run",
    ])

    assert output == [
        'NAME:   nextcloud',
    ]


def test_config():
    os.environ["HELM_VAULT_KVVERSION"] = "v1"
    parsed = vault.parse_args()
    parser, _ = parsed.parse_known_args([
        'clean',
        '-f',
        './tests/test.yaml',
        "-v",
        "--environment",
        "test"
    ])
    r = vault.Config.create_from_env(parser)
    assert r.environment == "/test"
    assert isinstance(r.kvversion, vault.KVVersion)
    assert r.kvversion, vault.KVVersion.v1


def test_decode_file_1():
    parsed = vault.parse_args()
    obj = vault.HelmVault(
        *parsed.parse_known_args([
            "enc", "-f", "test.yaml"
        ])
    )
    assert obj.decode_file == "test.yaml.dec"


def test_decode_file_2_env():
    parsed = vault.parse_args()
    obj = vault.HelmVault(
        *parsed.parse_known_args([
            "enc", "-e", "prod", "-f", "test.yaml"
        ])
    )
    assert obj.decode_file == "test.yaml.prod.dec"
