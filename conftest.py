import os
import shutil
import subprocess
import sys

import pytest

# Ensure the project root is importable when running the test suite directly.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def self_signed(tmp_path):
    """Generate a throwaway self-signed cert/key pair, skipping if openssl is absent."""
    openssl = shutil.which('openssl')
    if openssl is None:
        pytest.skip('openssl is not available to generate a test certificate')
    cert, key = tmp_path / 'cert.pem', tmp_path / 'key.pem'
    subprocess.run(
        [openssl, 'req', '-x509', '-newkey', 'rsa:2048', '-nodes',
         '-keyout', str(key), '-out', str(cert), '-days', '1', '-subj', '/CN=localhost'],
        check=True, capture_output=True,
    )
    return str(cert), str(key)
