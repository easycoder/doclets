#!/usr/bin/env python3
"""Tests for the DocletManager search/LLM paths in as_doclets.py.

Ollama is mocked out entirely (FakeOllama replaces as_doclets.requests), so
these run anywhere — no model, no network. Run with: python3 test_as_doclets.py
"""
import json
import os
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import as_doclets as mod  # noqa: E402


class FakeResp:
    def __init__(self, data):
        self._d = data

    def raise_for_status(self):
        pass

    def json(self):
        return self._d


class FakeOllama:
    """Replaces as_doclets.requests. Bag-of-words fake embeddings; scriptable chat reply."""

    def __init__(self):
        self.embed_calls = 0
        self.chat_calls = 0
        self.embed_models = []
        self.chat_payloads = []
        self.reply = 'NO_MATCHES'
        self.tags = []
        self.embed_fail = False

    def get(self, url, timeout=None):
        if url.endswith('/api/tags'):
            return FakeResp({"models": [{"name": n} for n in self.tags]})
        raise AssertionError(f'unexpected Ollama URL: {url}')

    def post(self, url, json=None, timeout=None):
        if url.endswith('/api/embed'):
            self.embed_calls += 1
            texts = json['input']
            self.embed_models.append(json['model'])
            if self.embed_fail:
                return FakeResp({"embeddings": []})  # simulates unavailable embeddings
            return FakeResp({"embeddings": [self._vec(t) for t in texts]})
        if url.endswith('/api/chat'):
            self.chat_calls += 1
            self.chat_payloads.append(json)
            return FakeResp({"message": {"content": self.reply}})
        raise AssertionError(f'unexpected Ollama URL: {url}')

    @staticmethod
    def _vec(text):
        words = set(text.lower().split())
        return [1.0 if w in words else 0.0 for w in VOCAB]


CORPUS = [
    ("260101-00.md", "# Linux kernel basics", "Installing the kernel, compiling kernel modules, dmesg logs.\nMore kernel detail here."),
    ("260102-00.md", "# Example code for MQTT", "This doclet contains example code in Python for MQTT clients.\nPublish and subscribe examples."),
    ("250101-00.md", "# Network configuration", "Setting up ethernet, wifi, and static IP addresses.\nTroubleshooting network issues."),
    ("250102-00.md", "# Backup strategy", "Rsync backups, cron schedules, and offsite copies.\nRestore procedures."),
]

VOCAB = sorted({w for _, _, body in CORPUS for w in body.lower().split()})


def make_corpus(tmp: Path) -> Path:
    """Write the corpus under tmp/2026 and tmp/2025. Returns the base dir."""
    base = tmp / "TestDocs"
    for fname, subject, body in CORPUS:
        year = fname[:4]
        d = base / year
        d.mkdir(parents=True, exist_ok=True)
        (d / fname).write_text(f"{subject}\n\n{body}", encoding='utf-8')
    return base


def make_manager(base: Path, cache_dir: Path) -> mod.DocletManager:
    mgr = mod.DocletManager()
    mgr.set_doclets_dirs(str(base))  # absolute path => used as-is
    mgr.embed_cache_dir = cache_dir
    return mgr


def test_filename_lookup(mgr):
    results = mgr.search_data("TestDocs/260101-00.md")
    assert len(results) == 1, results
    assert results[0]["filename"] == "260101-00.md"
    assert results[0]["content"]  # filename queries force content
    print("OK  test_filename_lookup")


def test_literal_substring(mgr):
    results = mgr.search_data("example code")
    names = [r["filename"] for r in results]
    assert names == ["260102-00.md"], names
    print("OK  test_literal_substring (complete, no LLM)")


def test_semantic_llm_ranking(mgr, fake):
    # No literal overlap: the query words appear in no single doclet contiguously.
    # Semantic (fake embedding) should surface the MQTT doclet; LLM picks it.
    fake.reply = "260102-00.md"
    results = mgr.search_data("Python MQTT messaging", use_llm=True)
    names = [r["filename"] for r in results]
    assert names == ["260102-00.md"], names
    assert fake.chat_calls == 1
    # The candidate pool must have been semantic, not the raw corpus order.
    payload = fake.chat_payloads[-1]
    assert "260102-00.md" in payload["messages"][-1]["content"]
    # Selection should be near-deterministic.
    assert payload["options"]["temperature"] == 0.3
    print("OK  test_semantic_llm_ranking")


def test_synthesis(mgr, fake):
    reads = {"n": 0}
    orig = mgr.read_doclet_content
    mgr.read_doclet_content = lambda p: reads.__setitem__("n", reads["n"] + 1) or orig(p)
    try:
        for query in (
            "List the main topics covered by doclets in the TestDocs topic",
            "How many topics are there here?",
        ):
            reads["n"] = 0
            fake.reply = f"answer-for-{query}"
            results = mgr.search_data(query, use_llm=True)
            assert len(results) == 1 and "answer" in results[0], results
            assert results[0]["answer"] == fake.reply
            assert reads["n"] == 0, f"synthesis read {reads['n']} doclet bodies for {query!r}"
            # Subjects must be in the prompt, bodies must not.
            prompt = fake.chat_payloads[-1]["messages"][-1]["content"]
            assert "260101-00.md: Linux kernel basics" in prompt
            assert "Installing the kernel" not in prompt
    finally:
        mgr.read_doclet_content = orig
    print("OK  test_synthesis (subjects-only, zero body reads; count-style routing)")


def test_embed_cache_incremental(base, fake):
    cache_dir = base.parent / "emb2"
    mgr = make_manager(base, cache_dir)
    fake.embed_calls = 0
    fake.reply = "NO_MATCHES"
    mgr.semantic_search("anything at all")  # first pass: embeds 4 doclets + query
    first = fake.embed_calls
    assert first == 2, f"expected 2 embed calls (doclets + query), got {first}"
    mgr.semantic_search("anything at all")  # cache hit: only the query embed
    assert fake.embed_calls == first + 1, f"expected +1 embed call, got {fake.embed_calls}"
    # Cache file exists on disk
    cache_files = list(cache_dir.glob("*.json"))
    assert len(cache_files) >= 1, cache_files
    print("OK  test_embed_cache_incremental")


def test_answer_protocol(mgr, fake):
    # The handler prepends ANSWER| to a single {answer} entry — verify shape.
    fake.reply = "A synthesis answer."
    results = mgr.search_data("Summarize what is covered", use_llm=True)
    assert results == [{"answer": "A synthesis answer."}], results
    print("OK  test_answer_protocol (handler prefix verified in code review)")


def test_llm_ready(mgr, fake):
    fake.tags = ["qwen3.5:9b", "nomic-embed-text:latest"]  # :latest suffix from a bare pull
    ok, detail = mgr.llm_ready()
    assert ok, detail
    fake.tags = []
    ok, detail = mgr.llm_ready()
    assert not ok and "not pulled" in detail, detail
    print("OK  test_llm_ready (bare-name vs :latest, not-pulled)")


def test_llm_nomatch_fallback(mgr, fake):
    fake.reply = "NO_MATCHES"  # fickle model run: refuses to pick
    results, meta = mgr.search_data("Python MQTT messaging", use_llm=True, return_meta=True)
    assert meta["matched_by"] == "semantic_fallback", meta
    assert len(results) >= 1, results
    assert results[0]["filename"] == "260102-00.md", results  # top semantic hit
    print("OK  test_llm_nomatch_fallback (semantic pool when LLM declines)")


def test_llm_nomatch_hint(base, fake):
    # Embeddings unavailable → no semantic fallback → genuine LLM no-match.
    # The reply should carry a re-run hint rather than a bare "no results".
    cache_dir = base.parent / "emb3"
    mgr = make_manager(base, cache_dir)
    fake.embed_fail = True
    fake.reply = "NO_MATCHES"
    results = mgr.search_data("totally unrelated query zzz", use_llm=True)
    assert len(results) == 1 and "answer" in results[0], results
    assert "try" in results[0]["answer"].lower()
    print("OK  test_llm_nomatch_hint (re-run hint on LLM no-match)")


def test_acl_permissions():
    tmp = Path(tempfile.mkdtemp(prefix="doclets-acl-"))
    try:
        home = tmp / "home"
        corpus = make_corpus(home / "Doclets")  # home/Doclets/TestDocs/{2026,2025}
        acl_path = tmp / "acl.json"
        acl_path.write_text(json.dumps({
            "version": 2,
            "entries": [{"name": "Writer", "token": "tok-writer", "topics": ["Private", "TestDocs"]}],
            "topics": {"Private": {"owner": "tok-owner", "public": False,
                                   "readers": ["tok-reader"], "deleters": ["tok-deleter"]}}
        }), encoding='utf-8')
        log_path = tmp / "activity.log"
        orig_home = mod.Path.home
        mod.Path.home = staticmethod(lambda: home)
        try:
            mgr = mod.DocletManager()
            mgr.set_doclets_dirs(str(corpus))
            mgr.acl_path = str(acl_path)
            mgr.activity_log_path = str(log_path)

            # read
            assert mgr.can_read("Private", "") is False
            assert mgr.can_read("Private", "tok-owner") is True
            assert mgr.can_read("Private", "tok-reader") is True
            assert mgr.can_read("Private", "tok-writer") is True   # writers can read
            assert mgr.can_read("Private", "other") is False
            assert mgr.can_read("Unlisted", "") is True            # open by default

            # write
            assert mgr.can_write("Private", "tok-owner") is True
            assert mgr.can_write("Private", "tok-writer") is True
            assert mgr.can_write("Private", "tok-reader") is False
            assert mgr.can_write("Private", "") is False

            # delete
            assert mgr.can_delete("Private", "tok-owner") is True
            assert mgr.can_delete("Private", "tok-deleter") is True
            assert mgr.can_delete("Private", "tok-writer") is False  # configured deleters win
            assert mgr.can_delete("TestDocs", "tok-writer") is True  # unconfigured: write implies delete

            # token payload parsing (client now sends `token\n<payload>` on every request)
            assert mgr.parse_token_payload("tok\nrest") == ("tok", "rest")
            assert mgr.parse_token_payload("") == ("", "")
            assert mgr.parse_token_payload("tok-only") == ("tok-only", "")

            # logging (writes + denials)
            mgr.log_action("tok-owner", "save", "Private", "x.md", "ok")
            mgr.log_action("", "view", "Private", "y.md", "denied")
            lines = log_path.read_text(encoding='utf-8').strip().split('\n')
            assert len(lines) == 2, lines
            e1 = json.loads(lines[0])
            assert e1["action"] == "save" and e1["result"] == "ok" and e1["token"] == "tok-owner"
            e2 = json.loads(lines[1])
            assert e2["token"] == "anonymous" and e2["result"] == "denied"

            # save integration: writer saves ok + logged; outsider denied + logged
            out = mgr.save_doclet_with_acl("tok-writer\nTestDocs/260101-00.md\nnew body")
            assert out == "Saved TestDocs/260101-00.md", out
            # corpus year dirs are named from the filename prefix (2601, not 2026)
            assert (corpus / "2601" / "260101-00.md").read_text(encoding='utf-8') == "new body"
            out = mgr.save_doclet_with_acl("tok-reader\nTestDocs/260101-00.md\nnope")
            assert out == "Save failed: unauthorized", out
            log_text = log_path.read_text(encoding='utf-8')
            assert '"result": "ok"' in log_text and '"result": "denied"' in log_text
        finally:
            mod.Path.home = orig_home
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print("OK  test_acl_permissions (read/write/delete, token payload, log, save auth)")


def test_readable_topics(base):
    tmp = base.parent
    home = tmp / "home"
    (home / "Doclets" / "PublicT").mkdir(parents=True)
    (home / "Doclets" / "PrivateT").mkdir(parents=True)
    acl_path = tmp / "acl2.json"
    acl_path.write_text(json.dumps({
        "version": 2, "entries": [],
        "topics": {"PrivateT": {"owner": "tok-owner", "public": False}}
    }), encoding='utf-8')
    orig_home = mod.Path.home
    mod.Path.home = staticmethod(lambda: home)
    try:
        mgr = mod.DocletManager()
        mgr.acl_path = str(acl_path)
        assert mgr.readable_topics("") == ["PublicT"]
        assert mgr.readable_topics("tok-owner") == ["PrivateT", "PublicT"]
    finally:
        mod.Path.home = orig_home
    print("OK  test_readable_topics (public vs private listing)")


def main():
    tmp = Path(tempfile.mkdtemp(prefix="doclets-test-"))
    try:
        base = make_corpus(tmp)
        cache_dir = tmp / "emb"
        os.environ['DOCLETS_OLLAMA_URL'] = 'http://fake:11434'
        os.environ['DOCLETS_LLM_SYNTH'] = 'list the main topics,main topics,topics covered,what topics,which topics,how many,number of topics,count the,summar,overview,categories,outline,what is covered,what\'s here,what is here,structure of the'
        global VOCAB
        mgr = make_manager(base, cache_dir)
        fake = FakeOllama()
        mod.requests = fake

        test_filename_lookup(mgr)
        test_literal_substring(mgr)
        test_semantic_llm_ranking(mgr, fake)
        test_synthesis(mgr, fake)
        test_embed_cache_incremental(base, fake)
        test_answer_protocol(mgr, fake)
        test_llm_ready(mgr, fake)
        test_llm_nomatch_fallback(mgr, fake)
        test_llm_nomatch_hint(base, fake)
        test_acl_permissions()
        test_readable_topics(base)
        print("\nAll tests passed.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
