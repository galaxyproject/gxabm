
from lib.common import get_env, Context


def test_get_env():
    context = Context('server', 'key', 'kubeconfig')
    assert context.GALAXY_SERVER == 'server'
    assert context.API_KEY == 'key'
    assert context.KUBECONFIG == 'kubeconfig'
    env = get_env(context)
    assert env is not None

