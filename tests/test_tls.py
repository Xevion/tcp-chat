import ssl

from shared import tls


def test_client_context_without_verification():
    context = tls.client_context(verify=False)
    assert context.verify_mode == ssl.CERT_NONE
    assert context.check_hostname is False


def test_client_context_with_verification():
    context = tls.client_context(verify=True)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True
