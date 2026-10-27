import verifier as v

def test_syntax():
    for bad in ["plain", "a@b", "a..b@x.com", "@x.com", "a b@x.com"]:
        assert v.check(bad)["status"] == "bounce"

def test_typo_hint():
    assert v.suggest("gmial.com") == "gmail.com"
    assert v.suggest("gmail.com") is None

def test_opaque(monkeypatch):
    monkeypatch.setattr(v, "mx_hosts", lambda d: ["mx.example"])
    assert v.check("x@yahoo.com")["status"] == "unknown"

def test_no_domain(monkeypatch):
    monkeypatch.setattr(v, "mx_hosts", lambda d: None)
    assert v.check("x@nope.invalid")["status"] == "bounce"

def test_smtp_paths(monkeypatch):
    monkeypatch.setattr(v, "mx_hosts", lambda d: ["mx.example"])
    monkeypatch.setattr(v, "smtp_available", lambda: True)
    monkeypatch.setattr(v, "is_catch_all", lambda h, d: False)
    for code, want in [(250, "deliverable"), (550, "bounce"), (451, "unknown")]:
        monkeypatch.setattr(v, "rcpt", lambda h, a, c=code: c)
        assert v.check("x@corp.example")["status"] == want
    monkeypatch.setattr(v, "is_catch_all", lambda h, d: True)
    monkeypatch.setattr(v, "rcpt", lambda h, a: 250)
    assert v.check("x@corp.example")["status"] == "unknown"
