"""Tests for token-usage accounting and cost estimation."""

from types import SimpleNamespace

from project_june.usage import MODEL_PRICES, Usage


def usage_obj(**kw):
    base = {
        "input_tokens": 0,
        "output_tokens": 0,
        "cache_read_input_tokens": 0,
        "cache_creation_input_tokens": 0,
    }
    base.update(kw)
    return SimpleNamespace(**base)


def test_add_accumulates_and_counts_turns():
    u = Usage()
    u.add(usage_obj(input_tokens=100, output_tokens=50))
    u.add(usage_obj(input_tokens=30, output_tokens=20, cache_read_input_tokens=200))
    assert u.input_tokens == 130
    assert u.output_tokens == 70
    assert u.cache_read_input_tokens == 200
    assert u.turns == 2
    assert u.total_input_tokens == 330


def test_add_ignores_none():
    u = Usage()
    u.add(None)
    assert u.turns == 0


def test_cost_uses_price_table():
    u = Usage(input_tokens=1_000_000, output_tokens=1_000_000)
    in_price, out_price = MODEL_PRICES["claude-opus-4-8"]
    assert u.cost("claude-opus-4-8") == in_price + out_price


def test_cost_discounts_cache_reads():
    full = Usage(input_tokens=1_000_000)
    cached = Usage(cache_read_input_tokens=1_000_000)
    # Cache reads are billed at ~0.1x the uncached input price.
    assert cached.cost("claude-opus-4-8") < full.cost("claude-opus-4-8")
    assert abs(cached.cost("claude-opus-4-8") - full.cost("claude-opus-4-8") * 0.1) < 1e-9


def test_cost_unknown_model_is_zero():
    assert Usage(input_tokens=1_000).cost("made-up-model") == 0.0


def test_add_combines():
    combined = Usage(input_tokens=10, turns=1) + Usage(input_tokens=5, output_tokens=2, turns=1)
    assert combined.input_tokens == 15
    assert combined.output_tokens == 2
    assert combined.turns == 2
