import numpy as np
from scipy.stats import uniform, loguniform

from mango.domain.domain_space import DomainSpace
from mango.domain.parameter_sampler import ParameterSampler
from mango.domain.distribution import loguniform as mango_loguniform


def test_domain():
    params = {
        "a": range(10),
        "b": np.random.randint(0, 1e6, size=50),
        "d": [1, 0.1, 2.0],
        "e": ["a", 1, "b", "c", None],
        "f": ["1", "-1"],
        "h": [True, False],
    }
    sampler = ParameterSampler(params)
    sampler.domain_size = 1000
    ds = DomainSpace(sampler)
    assert all(k in sampler.integer_params for k in ["a", "b"])
    assert all(k in sampler.categorical_params for k in ["d", "e", "f", "h"])
    samples = ds.get_domain()

    for sample in samples:
        for param in params.keys():
            assert sample[param] in params[param]

    params = {
        "a": [1],
    }
    sampler = ParameterSampler(params)
    sampler.domain_size = 1000
    ds = DomainSpace(sampler)
    assert all(k in sampler.integer_params for k in ["a"])
    samples = ds.get_domain()

    for sample in samples:
        for param in params.keys():
            assert sample[param] in params[param]


def test_mango_loguniform():
    params = {"a": mango_loguniform(-3, 6)}
    sampler = ParameterSampler(params)
    sampler.domain_size = 1000
    ds = DomainSpace(sampler)
    samples = ds.get_domain()
    assert all(1e-3 < sample["a"] < 1e3 for sample in samples)


def test_gp_samples_to_params():
    params = {
        "a": range(10),
        "b": uniform(-10, 20),
        "c": ["cat1", 1, "cat2"],
        "e": [1, 2, 3],
        "f": ["const"],
        "g": loguniform(0.001, 100),
        "h": [10],
    }

    sampler = ParameterSampler(params)
    sampler.domain_size = 1000
    ds = DomainSpace(sampler)

    X = np.array(
        [
            # 4, -8, 'cat2', 1, 'const', 1 , 10
            [4, -8, 0, 0, 1, 1, 1, 1, 10],
            # 0, -10.0, 'cat1', 3, 'const', 0.001 , 10
            [0, -10, 1, 0, 0, 3, 1, 0.001, 10],
            # 9, 10.0, 1, 2, 'const', 100 , 10
            [9, 10.0, 0, 1, 0, 2, 1, 100.0, 10],
        ]
    )
    calculated = ds.convert_PS_space(X)
    expected = [
        dict(a=4, b=-8.0, c="cat2", e=1, f="const", g=1, h=10),
        dict(a=0, b=-10.0, c="cat1", e=3, f="const", g=0.001, h=10),
        dict(a=9, b=10.0, c=1, e=2, f="const", g=100, h=10),
    ]

    for calc, exp in zip(calculated, expected):
        for k, v in calc.items():
            if k == "g":
                assert np.isclose(v, exp[k])
            else:
                assert v == exp[k]


def test_gp_space():
    params = {
        "f": range(10),
        "h": uniform(-10, 20),
        "e": ["cat1", 1, "cat2"],
        "c": [1, 2, 3],
        "a": ["const"],
        "g": loguniform(0.001, 100),
        "b": [10],
        "d": uniform(0, 1),
        "i": [True, False],
    }

    sampler = ParameterSampler(params)
    sampler.domain_size = 10000
    ds = DomainSpace(sampler)
    domain_list = ds.get_domain()
    X = ds.convert_GP_space(domain_list)

    assert (X[:, 0] == 1.0).all()  # a
    assert (X[:, 1] == 10.0).all()  # b
    assert np.isin(X[:, 2], [1, 2, 3]).all()  # c
    assert np.isin(X[:, 4:7], np.eye(3)).all()  # e
    assert X.shape == (sampler.domain_size, 12)

    samples = ds.convert_PS_space(X)

    for sample in samples:
        assert sample["a"] == "const"
        assert sample["b"] == 10
        assert sample["c"] in params["c"]
        assert 0.0 <= sample["d"] <= 1.0
        assert sample["e"] in params["e"]
        assert sample["f"] in params["f"]
        assert 0.001 <= sample["g"] <= 100
        assert -10 <= sample["h"] <= 10
        assert sample["i"] in params["i"]

    X2 = ds.convert_GP_space(samples)
    assert np.isclose(X2, X).all()


def test_constraint():
    param_dict = dict(
        p1=["a", "b", "c"],
        p2=uniform(0, 1),
    )

    def constraint(samples):
        p1 = np.array([s["p1"] for s in samples])
        p2 = np.array([s["p2"] for s in samples])
        return ((p1 == "a") & (p2 < 0.5)) | ((p1 != "a") & (p2 >= 0.5))

    sampler = ParameterSampler(param_dict)
    sampler.domain_size = 100
    ds = DomainSpace(sampler, constraint=constraint)
    samples = ds.get_domain()
    assert len(samples) == 100
    assert all(constraint(samples))


def test_np_space():
    param_dict = {
        "x": np.array(["a", "b", "c"]),
        "y": np.arange(100),
    }
    sampler = ParameterSampler(param_dict)
    sampler.domain_size = 10
    ds = DomainSpace(sampler)
    params = ds.get_domain()
    assert len(params) == 10

    gp_params = ds.convert_GP_space(params)
    assert gp_params.shape == (10, 4)
