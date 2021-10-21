# Copyright 2016-2021 Swiss National Supercomputing Centre (CSCS/ETH Zurich)
# ReFrame Project Developers. See the top-level LICENSE file for details.
#
# SPDX-License-Identifier: BSD-3-Clause

import pytest

import reframe as rfm
import unittests.utility as test_util
import reframe.core.fixtures as fixtures
import reframe.core.runtime as rt
import reframe.utility.udeps as udeps
from reframe.core.exceptions import ReframeSyntaxError


def test_fixture_class_types():
    class Foo:
        pass

    # Wrong fixture classes

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(Foo)

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionMixin)

    # Session and partition scopes must be run-only.

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, scope='session')

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, scope='partition')

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.CompileOnlyRegressionTest, scope='session')

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.CompileOnlyRegressionTest, scope='partition')


def test_fixture_args():
    '''Test invalid fixture arguments.'''
    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, scope='other')

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, action='other')

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, variants='other')

    with pytest.raises(TypeError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(rfm.RegressionTest, variables='other')


def test_abstract_fixture():
    '''Can't register an abstract fixture.'''

    class Foo(rfm.RegressionTest):
        p = parameter()

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(Foo)


def test_fixture_variants():
    '''Fixtures must have at least one valid variant.'''

    class Foo(rfm.RegressionTest):
        p = parameter(range(4))

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(Foo, variants={'p': lambda x: x > 10})

    with pytest.raises(ValueError):
        class MyTest(rfm.RegressionMixin):
            f = fixture(Foo, variants=())

    # Test default variants argument 'all'
    class MyTest(rfm.RegressionMixin):
        f = fixture(Foo, variants='all')

    assert MyTest.fixture_space['f'].variants == (0, 1, 2, 3,)


def test_fork_join_variants():
    '''Test fork/join toggle on the variants.'''

    class Foo(rfm.RegressionTest):
        p = parameter(range(4))

    class MyTest(rfm.RegressionMixin):
        f0 = fixture(Foo, action='fork')
        f1 = fixture(Foo, action='join')

    assert MyTest.num_variants == 4
    assert MyTest.fixture_space['f0'].variants == (0, 1, 2, 3)
    assert MyTest.fixture_space['f1'].variants == (0, 1, 2, 3)

    # The fork action has only one variant per fork
    assert MyTest.fixture_space['f0'].fork_variants == ((0,), (1,), (2,), (3,))

    # The join action has only one fork with all the variants in it
    assert MyTest.fixture_space['f1'].fork_variants == ((0, 1, 2, 3),)


def test_default_args():
    class Foo(rfm.RegressionMixin):
        f = fixture(rfm.RegressionTest)

    assert Foo.fixture_space['f'].variables == {}
    assert Foo.fixture_space['f'].action == 'fork'
    assert Foo.fixture_space['f'].scope == 'test'
    assert Foo.fixture_space['f'].variants == (0,)


def test_fixture_inheritance():
    class Fix(rfm.RunOnlyRegressionTest):
        pass

    class Foo(rfm.RegressionMixin):
        f0 = fixture(Fix, scope='test')

    class Bar(rfm.RegressionMixin):
        f1 = fixture(Fix, scope='environment')
        f2 = fixture(Fix, scope='partition')

    class Baz(Foo, Bar):
        f2 = fixture(Fix, scope='session')

    assert Baz.f0.scope == 'test'
    assert Baz.f1.scope == 'environment'
    assert Bar.f2.scope == 'partition'
    assert Baz.f2.scope == 'session'


def test_fixture_inheritance_clash():
    '''Fixture name clash is not permitted.'''

    class Foo(rfm.RegressionMixin):
        f0 = fixture(rfm.RegressionTest)

    class Bar(rfm.RegressionMixin):
        f0 = fixture(rfm.RegressionTest)

    # Multiple inheritance clash
    with pytest.raises(ReframeSyntaxError):
        class Baz(Foo, Bar):
            pass


def test_fixture_override():
    '''A child class may only redefine a fixture with the fixture builtin.'''

    class Foo(rfm.RegressionMixin):
        f0 = fixture(rfm.RegressionTest)

    class Bar(Foo):
        f0 = fixture(rfm.RegressionTest)

    with pytest.raises(ReframeSyntaxError):
        class Bar(Foo):
            f0 = 4


def test_fixture_space_access():
    class P0(rfm.RunOnlyRegressionTest):
        p0 = parameter(range(2))

    class Foo(rfm.RegressionMixin):
        f0 = fixture(P0, scope='test', action='fork')
        f1 = fixture(P0, scope='environment', action='join')
        f2 = fixture(P0, scope='partition', action='fork')
        f3 = fixture(P0, scope='session', action='join')

    assert len(rfm.RegressionTest.fixture_space) == 1

    # Foo has 4 variants
    assert len(Foo.fixture_space) == 4

    # Foo has 4 fixtures
    assert len(Foo.fixture_space.fixtures) == 4

    # Assert the fixture variant ID combination for each of the Foo variants
    assert [v for v in Foo.fixture_space] == [((0, 1), (0,), (0, 1), (0,)),
                                              ((0, 1), (0,), (0, 1), (1,)),
                                              ((0, 1), (1,), (0, 1), (0,)),
                                              ((0, 1), (1,), (0, 1), (1,))]

    # Get the k-v map for Foo's variant #2
    assert Foo.fixture_space[2] == {'f0': (0,),
                                    'f1': (0, 1),
                                    'f2': (1,),
                                    'f3': (0, 1)}

    # Access the fixture space by fixture name - get the fixture object
    assert Foo.fixture_space['f1'].cls == P0
    assert Foo.fixture_space['f1'].scope == 'environment'
    assert Foo.fixture_space['f1'].action == 'join'


def test_fixture_data():
    '''Test the structure that holds the raw fixture data in the registry.'''

    d = fixtures.FixtureData(1, 2, 3, 4)
    assert d.data == (1, 2, 3, 4,)
    assert d.variant_num == 1
    assert d.environments == 2
    assert d.partitions == 3
    assert d.variables == 4


@pytest.fixture
def fixture_sys(make_exec_ctx_g):
    yield from make_exec_ctx_g(test_util.TEST_CONFIG_FILE, 'sys1')


@pytest.fixture
def simple_fixture():
    class MyFixture(rfm.RunOnlyRegressionTest):
        v = variable(int, value=1)

    def _fixture_wrapper(**kwargs):
        return fixtures.TestFixture(MyFixture, **kwargs)

    yield _fixture_wrapper


@pytest.fixture
def param_fixture():
    class MyFixture(rfm.RunOnlyRegressionTest):
        p = parameter(range(2))

    def _fixture_wrapper(**kwargs):
        return fixtures.TestFixture(MyFixture, **kwargs)

    yield _fixture_wrapper


def test_fixture_registry_all(fixture_sys, simple_fixture):
    '''Test with all valid partition and environments available.'''

    reg = fixtures.FixtureRegistry()

    # Get all part and environs
    sys = rt.runtime().system
    all_part = [p.fullname for p in sys.partitions]
    all_env = [e.name for p in sys.partitions for e in p.environs]

    registered_fix = set()

    def register(s, **kwargs):
        registered_fix.update(
            reg.add(simple_fixture(scope=s, **kwargs),
                    0, 'base', all_part, set(all_env))
        )

    register('test')
    assert len(registered_fix) == 1
    register('environment')
    assert len(registered_fix) == 1 + len(all_env)
    register('partition')
    assert len(registered_fix) == 1 + len(all_env) + len(all_part)
    register('session')
    assert len(registered_fix) == 2 + len(all_env) + len(all_part)

    # Test the __getitem__ method
    names = reg[simple_fixture().cls].keys()
    assert len(names) == len(registered_fix)

    # Test the __contains__ method
    assert simple_fixture().cls in reg


def test_fixture_registry_edges(fixture_sys, simple_fixture):
    '''Test edge cases.'''

    reg = fixtures.FixtureRegistry()
    registered_fix = set()

    def register(p, e, **kwargs):
        registered_fix.update(
            reg.add(simple_fixture(**kwargs),
                    0, 'b', p, e)
        )

    # Invalid partitions - NO-OP
    register(['wrong_partition'], ['e1', 'e2'])
    assert len(registered_fix) == 0

    # Valid partition but wrong environment - NO-OP (except test scope)
    partitions = [p.fullname for p in rt.runtime().system.partitions]
    register([partitions[0]], ['wrong_environment'], scope='session')
    assert len(registered_fix) == 0
    register([partitions[0]], ['wrong_environment'], scope='partition')
    assert len(registered_fix) == 0
    register([partitions[0]], ['wrong_environment'], scope='environment')
    assert len(registered_fix) == 0
    register([partitions[0]], ['wrong_environment'], scope='test')
    assert len(registered_fix) == 1
    registered_fix.pop()

    # Environ 'e2' is not supported in 'sys1:p0', but is in 'sys1:p1'
    register(['sys1:p0', 'sys1:p1'], ['e2'], scope='session')
    assert 'e2' not in {env.name for p in rt.runtime().system.partitions
                        if p.fullname == 'sys1:p0' for env in p.environs}
    assert 'e2' in {env.name for p in rt.runtime().system.partitions
                    if p.fullname == 'sys1:p1' for env in p.environs}
    assert len(registered_fix) == 1

    # 'sys1:p0' is skipped on this fixture because env 'e2' is not supported
    last_fixture = reg[simple_fixture().cls][registered_fix.pop()]
    assert last_fixture.partitions == ['sys1:p1']
    assert last_fixture.environments == ['e2']

    # Similar behavior withe the partition scope
    register(['sys1:p0', 'sys1:p1'], ['e2'], scope='partition')
    assert len(registered_fix) == 1
    last_fixture = reg[simple_fixture().cls][registered_fix.pop()]
    assert last_fixture.partitions == ['sys1:p1']
    assert last_fixture.environments == ['e2']

    # And also similar behavior withe the environment scope
    register(['sys1:p0', 'sys1:p1'], ['e2'], scope='environment')
    assert len(registered_fix) == 1
    last_fixture = reg[simple_fixture().cls][registered_fix.pop()]
    assert last_fixture.partitions == ['sys1:p1']
    assert last_fixture.environments == ['e2']

    # However, with the test scope partitions and environments get copied
    # without any filtering.
    register(['sys1:p0', 'sys1:p1'], ['e2'], scope='test')
    assert len(registered_fix) == 1
    last_fixture = reg[simple_fixture().cls][registered_fix.pop()]
    assert last_fixture.partitions == ['sys1:p0', 'sys1:p1']
    assert last_fixture.environments == ['e2']


def test_fixture_registry_variables(fixture_sys, simple_fixture):
    '''Test the order of the variables does not matter.'''

    reg = fixtures.FixtureRegistry()

    # Get one valid part+env combination
    sys = rt.runtime().system
    part = sys.partitions[0].fullname
    env = sys.partitions[0].environs[0].name
    registered_fix = set()

    def register(**kwargs):
        registered_fix.update(
            reg.add(simple_fixture(**kwargs),
                    0, 'b', [part], [env])
        )

    register(variables={'a': 1, 'b': 2})
    assert len(registered_fix) == 1
    register(variables={'b': 2, 'a': 1})
    assert len(registered_fix) == 1

    # Fixture with different variables is treated as a new fixture.
    register(variables={'a': 2, 'b': 2})
    assert len(registered_fix) == 2
    register()
    assert len(registered_fix) == 3

    # Test also the format of the internal fixture tuple
    fixt_data = list(reg[simple_fixture().cls].values())[0]
    assert fixt_data.variant_num == 0
    assert fixt_data.environments == [env]
    assert fixt_data.partitions == [part]
    assert all((v in fixt_data.variables for v in ('b', 'a')))


def test_fixture_registry_variants(fixture_sys, param_fixture):
    '''Test different fixture variants are registered separately.'''

    reg = fixtures.FixtureRegistry()

    # Get one valid part+env combination
    sys = rt.runtime().system
    part = sys.partitions[0].fullname
    env = sys.partitions[0].environs[0].name
    registered_fix = set()

    def register(scope='test', variant=0):
        registered_fix.update(
            reg.add(param_fixture(scope=scope), variant,
                    'b', [part], [env])
        )

    register(scope='test', variant=0)
    assert len(registered_fix) == 1
    register(scope='test', variant=1)
    assert len(registered_fix) == 2
    register(scope='environment', variant=0)
    assert len(registered_fix) == 3
    register(scope='environment', variant=1)
    assert len(registered_fix) == 4
    register(scope='partition', variant=0)
    assert len(registered_fix) == 5
    register(scope='partition', variant=1)
    assert len(registered_fix) == 6
    register(scope='session', variant=0)
    assert len(registered_fix) == 7
    register(scope='session', variant=1)
    assert len(registered_fix) == 8


def test_fixture_registry_base_arg(fixture_sys, simple_fixture):
    '''The base argument argument only has an effect with test scope.'''

    reg = fixtures.FixtureRegistry()

    # Get one valid part+env combination
    sys = rt.runtime().system
    part = sys.partitions[0].fullname
    env = sys.partitions[0].environs[0].name
    registered_fix = set()

    def register(scope, base):
        registered_fix.update(
            reg.add(simple_fixture(scope=scope), 0,
                    base, [part], [env])
        )

    # For a test scope, the base name is used for the fixture name mangling.
    # So changing this base arg, leads to a new fixture being registered.
    register(scope='test', base='b1')
    assert len(registered_fix) == 1
    register(scope='test', base='b2')
    assert len(registered_fix) == 2

    # The base argument is not used with any of the other scopes.
    register(scope='environment', base='b1')
    assert len(registered_fix) == 3
    register(scope='environment', base='b2')
    assert len(registered_fix) == 3
    register(scope='partition', base='b1')
    assert len(registered_fix) == 4
    register(scope='partition', base='b2')
    assert len(registered_fix) == 4
    register(scope='session', base='b3')
    assert len(registered_fix) == 5
    register(scope='session', base='b3')
    assert len(registered_fix) == 5


def test_overlapping_registries(fixture_sys, simple_fixture, param_fixture):
    '''Test instantiate_all, update and difference registry methods.'''

    # Get one valid part+env combination
    sys = rt.runtime().system
    part = sys.partitions[0].fullname
    env = sys.partitions[0].environs[0].name

    # Build base registry with some fixtures
    reg = fixtures.FixtureRegistry()
    reg.add(simple_fixture(), 0, 'b', [part], [env])
    for i in param_fixture().variants:
        reg.add(param_fixture(), i, 'b', [part], [env])

    # Build overlapping registry
    other = fixtures.FixtureRegistry()
    other.add(simple_fixture(variables={'v': 2}), 0, 'b', [part], [env])
    for i in param_fixture().variants:
        other.add(param_fixture(), i, 'b', [part], [env])

    assert len(reg.instantiate_all()) == len(param_fixture().variants) + 1
    assert len(other.instantiate_all()) == len(param_fixture().variants) + 1

    # Test difference method
    diff_reg = other.difference(reg)
    inst = diff_reg.instantiate_all()

    # Assert the difference is only the simple fixture with custom variable v.
    # This also tests that the instantiate_all method sets the test variables
    # correctly.
    assert len(inst) == 1
    assert inst[0].v == 2
    assert inst[0].name == list(diff_reg[simple_fixture().cls].keys())[0]
    assert inst[0].valid_systems == [part]
    assert inst[0].valid_prog_environs == [env]

    # Test the difference method in the opposite direction
    diff_reg = reg.difference(other)
    inst = diff_reg.instantiate_all()
    assert len(inst) == 1
    assert inst[0].v == 1

    # Test the update method
    reg.update(other)
    assert len(reg.instantiate_all()) == len(param_fixture().variants) + 2


def test_expand_part_env(fixture_sys, simple_fixture):
    '''Test expansion of partitions and environments.'''

    class MyTest(rfm.RegressionTest):
        foo = simple_fixture(scope='test')

    # The fixture registry is not injected when no variant_num is provided
    assert not hasattr(MyTest(), '_rfm_fixture_registry')

    # Assert errors are raised when root test does not specify part and env
    with pytest.raises(ReframeSyntaxError, match="'valid_systems'"):
        MyTest(variant_num=0)

    MyTest.valid_systems = ['sys1']
    with pytest.raises(ReframeSyntaxError, match="'valid_prog_environs'"):
        MyTest(variant_num=0)

    # Test the part and envs got expanded properly by the registry. For this
    # the fixture must be of test scope, so that the envs and parts just get
    # passed along to the same fixture instance.

    def get_fixt_data(inst):
        '''Helper function to retrieve the fixture data'''
        return list(
            getattr(
                inst, '_rfm_fixture_registry'
            )[simple_fixture().cls].values()
        )[0]

    MyTest.valid_prog_environs = ['*']
    d = get_fixt_data(MyTest(variant_num=0))
    assert all(env in d.environments for env in ('e0', 'e1', 'e2', 'e3'))
    assert all(part in d.partitions for part in ('sys1:p0', 'sys1:p1'))

    # Repeat now using * for the valid_systems
    MyTest.valid_systems = ['*']
    d = get_fixt_data(MyTest(variant_num=0))
    assert all(part in d.partitions for part in ('sys1:p0', 'sys1:p1'))


def test_fixture_injection(fixture_sys, simple_fixture, param_fixture):
    '''Test the fixture injection.'''

    def get_injected_deps(**kwargs):
        class MyTest(rfm.RegressionTest):
            foo = simple_fixture(**kwargs)
            valid_systems = ['sys1:p0']
            valid_prog_environs = ['e0']

        return MyTest(variant_num=0).user_deps()[0]

    assert get_injected_deps(scope='session')[1] == udeps.fully
    assert get_injected_deps(scope='partition')[1] == udeps.by_part
    assert get_injected_deps(scope='environment')[1] == udeps.by_case
    assert get_injected_deps(scope='test')[1] == udeps.by_case

    # Test that parameterized fixtures with a join action inject multiple deps
    class MyTest(rfm.RegressionTest):
        foo = param_fixture(action='join')
        valid_systems = ['sys1:p0']
        valid_prog_environs = ['e0']

    assert len(
        MyTest(variant_num=0).user_deps()
    ) == len(param_fixture().variants)
