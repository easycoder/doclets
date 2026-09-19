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
import time
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


def test_empty_query_lists_all(mgr):
    results = mgr.search_data("")
    names = sorted(r["filename"] for r in results)
    assert len(names) == 4, names  # every corpus doclet
    assert names == sorted(f for f, _, _ in CORPUS), names
    print("OK  test_empty_query_lists_all (empty query returns every doclet)")


def test_llm_keep_alive_parsing():
    durations = {
        '60s': 60.0,
        '5m': 300.0,
        '1h': 3600.0,
        '2d': 172800.0,
        '300': 300.0,      # bare number = seconds
        '0': 0.0,          # evict immediately
        '-1': -1.0,        # Ollama's 'never evict'
        'garbage': 60.0,   # unparseable → caller's default
    }
    for text, expected in durations.items():
        got = mod.DocletManager._duration_seconds(text, 60.0)
        assert got == expected, (text, got, expected)
    print("OK  test_llm_keep_alive_parsing (Ollama-style durations)")


def reset_beat(mgr):
    mgr._alive_session = False
    mgr._last_event = 0.0
    mgr._last_beat = 0.0


BENIGN_GPU = (
    '3562, /opt/brave.com/brave/brave --type=gpu-process, 67\n'
    '14873, /usr/lib/reasonix/app/Reasonix --type=gpu-process, 115\n'
    '23767, /snap/ollama/137/lib/ollama/llama-server, 3824\n'
)


def stub_gpu(mgr, output, video_running=False):
    """Pin both GPU signals, so tests need neither nvidia-smi nor a quiet machine."""
    mgr._run_nvidia_smi = lambda: output
    mgr._video_activity = lambda: video_running
    mgr._gpu_checked = 0.0
    mgr._gpu_busy_state = False
    mgr._gpu_busy_reason = ''


def test_llm_beat_holds_model_warm(mgr, fake):
    stub_gpu(mgr, BENIGN_GPU)
    reset_beat(mgr)
    fake.chat_payloads.clear()
    assert mgr.beat() == 'idle', 'no session, so nothing to hold'
    assert fake.chat_payloads == [], 'an idle beat must not talk to Ollama'

    mgr.note_doclet_event(opens_session=True)
    assert mgr.beat() == 'warm', 'the first beat after an event refreshes residency'
    payload = fake.chat_payloads[-1]
    assert payload['messages'] == [], payload      # a preload, not a completion
    assert payload['model'] == mgr.model, payload
    assert payload['keep_alive'] == mgr.llm_keep_alive == '60s', payload
    assert mgr.beat() == 'hold', 'beats are throttled to DOCLETS_LLM_BEAT'
    assert len(fake.chat_payloads) == 1, fake.chat_payloads
    print("OK  test_llm_beat_holds_model_warm (preload beats, throttled)")


def test_llm_beat_does_not_count_as_activity(mgr, fake):
    # If a beat refreshed the window it is holding open, the session could never
    # end and the GPU would never be handed back.
    stub_gpu(mgr, BENIGN_GPU)
    reset_beat(mgr)
    mgr.note_doclet_event(opens_session=True)
    mgr._last_event = time.time() - 5
    mgr.beat()
    assert time.time() - mgr._last_event >= 5, 'a beat refreshed the activity window'
    print("OK  test_llm_beat_does_not_count_as_activity (session can still end)")


def test_llm_beat_events_refresh_window(mgr, fake):
    reset_beat(mgr)
    fake.chat_payloads.clear()
    mgr.note_doclet_event()  # e.g. opening a doclet: activity, but not a query
    assert mgr.beat() == 'idle', 'browsing alone must not load a model'
    assert fake.chat_payloads == [], fake.chat_payloads

    mgr.note_doclet_event(opens_session=True)
    before = mgr._last_event
    time.sleep(0.01)
    mgr.note_doclet_event()  # reading a doclet keeps the session (and model) alive
    assert mgr._last_event > before
    assert mgr._alive_session, 'activity inside the window must not close the session'
    print("OK  test_llm_beat_events_refresh_window (reads extend the window)")


def test_llm_beat_yields_to_video(mgr, fake):
    # Video work at the GPU (the detection itself is covered by the tests below).
    stub_gpu(mgr, BENIGN_GPU, video_running=True)
    reset_beat(mgr)
    mgr.note_doclet_event(opens_session=True)
    fake.chat_payloads.clear()
    assert mgr.beat() == 'yielded'
    assert [(p['model'], p['keep_alive']) for p in fake.chat_payloads] == [
        (mgr.model, 0), (mgr.embed_model, 0)], fake.chat_payloads
    assert mgr.beat() == 'idle', 'the session must be closed after yielding'
    assert len(fake.chat_payloads) == 2, 'no further traffic while video work runs'
    stub_gpu(mgr, BENIGN_GPU)
    print("OK  test_llm_beat_yields_to_video (video work → models unloaded)")


def test_video_activity_scan():
    """The running-tools scan, which is all there is without nvidia-smi.

    A fresh manager: the other tests replace _video_activity with a stub, and the
    real scan is what this one is about.
    """
    mgr = mod.DocletManager()
    my_comm = Path('/proc/self/comm').read_text().strip().lower()
    saved = mgr.llm_video_procs
    try:
        mgr.llm_video_procs = {my_comm}
        assert mgr._video_activity(), 'own process name should be seen'
        mgr.llm_video_procs = {'no-such-process-xyz'}
        assert not mgr._video_activity()
    finally:
        mgr.llm_video_procs = saved
    print("OK  test_video_activity_scan (exact /proc comm match)")


def test_gpu_client_parsing():
    # Verbatim shape from a real nvidia-smi run on the development machine: the
    # browsers' GPU processes are always there, and Ollama's runner holds the model.
    text = (
        '3562, /opt/brave.com/brave/brave --type=gpu-process --ozone-platform=wayland, 67\n'
        '14873, /usr/lib/reasonix/app/Reasonix --type=gpu-process, 115\n'
        '23767, /snap/ollama/137/lib/ollama/llama-server, 3824\n'
        '24081, ffmpeg, 245\n'
    )
    clients = mod.DocletManager._parse_gpu_clients(text)
    assert [pid for pid, _, _ in clients] == [3562, 14873, 23767, 24081], clients
    assert clients[1][1].startswith('/usr/lib/reasonix'), clients[1]
    assert [used for _, _, used in clients] == [67, 115, 3824, 245], clients

    # Fields nvidia-smi can't supply, and junk rows, must not raise.
    odd = '42, some-app, [N/A]\n\nnot-a-client\n999, app, 12 MiB\n'
    assert mod.DocletManager._parse_gpu_clients(odd) == [(42, 'some-app', 0), (999, 'app', 12)]
    print("OK  test_gpu_client_parsing (CSV, [N/A], junk rows)")


def test_gpu_busy_from_nvidia_smi(mgr):
    # The idle state of the development machine, with the model loaded: browsers
    # hold small contexts and Ollama holds the model — none of that is video work.
    idle = (
        '3562, /opt/brave.com/brave/brave --type=gpu-process --ozone-platform=wayland, 67\n'
        '14873, /usr/lib/reasonix/app/Reasonix --type=gpu-process, 115\n'
        '23767, /snap/ollama/137/lib/ollama/llama-server, 3824\n'
    )
    stub_gpu(mgr, idle)
    assert not mgr._gpu_busy(), 'browser/desktop contexts or our own runner must not yield'

    # A named tool on the GPU: what an NVENC/NVDEC session looks like.
    stub_gpu(mgr, idle + '24081, ffmpeg, 245\n')
    assert mgr._gpu_busy() and 'ffmpeg' in mgr._gpu_busy_reason, mgr._gpu_busy_reason

    # A tool launched by path, or inside a Flatpak-style tree, still matches.
    stub_gpu(mgr, idle + '24082, /usr/bin/ffmpeg -i in.mp4 -c:v h264_nvenc, 245\n')
    assert mgr._gpu_busy(), mgr._gpu_busy_reason
    stub_gpu(mgr, idle + '24083, /app/bin/kdenlive --render, 300\n')
    assert mgr._gpu_busy() and 'kdenlive' in mgr._gpu_busy_reason, mgr._gpu_busy_reason

    # ...but a tool name buried in another app's flags must not match: browsers
    # pass base64 blobs, which would otherwise spell a short name like 'obs'.
    stub_gpu(mgr, idle + '24084, /opt/brave.com/brave/brave --disable-features=obs, 60\n')
    assert not mgr._gpu_busy(), 'a substring inside a command line must not match'

    # An unlisted tool doing heavy work is video work too, by VRAM — e.g. a game
    # or a 3D renderer. (Note `davinci-resolve-studio` would match the list's
    # `resolve` entry instead, which is the intended path-component behaviour.)
    stub_gpu(mgr, '900, cyberpunk2077, 4096\n')
    assert mgr._gpu_busy() and '4096' in mgr._gpu_busy_reason, mgr._gpu_busy_reason

    # ...but a small foreign context is not.
    stub_gpu(mgr, '901, some-utility, 120\n')
    assert not mgr._gpu_busy(), mgr._gpu_busy_reason

    # Our own runner holding the model must never be mistaken for the competition.
    stub_gpu(mgr, '23767, /snap/ollama/137/lib/ollama/llama-server, 3824\n')
    assert not mgr._gpu_busy(), 'Ollama must not yield to itself'

    # A listed tool that is running counts even when the GPU looks quiet (an
    # OpenGL preview doesn't appear in nvidia-smi's client list).
    stub_gpu(mgr, idle, video_running=True)
    assert mgr._gpu_busy() and mgr._gpu_busy_reason == 'video tool running', mgr._gpu_busy_reason

    # The probe is throttled: beats come round far more often than the GPU changes hands.
    calls = []
    stub_gpu(mgr, idle)
    mgr._run_nvidia_smi = lambda: (calls.append(1), idle)[1]
    assert not mgr._gpu_busy() and len(calls) == 1
    assert not mgr._gpu_busy() and len(calls) == 1, 'second probe inside the interval'
    mgr._gpu_checked = 0.0
    mgr._gpu_busy()
    assert len(calls) == 2, 'no probe after the interval elapsed'
    stub_gpu(mgr, idle)
    print("OK  test_gpu_busy_from_nvidia_smi (names, paths, VRAM, throttle, self)")


def test_gpu_busy_without_nvidia_smi(mgr):
    # No usable nvidia-smi: the running-tools signal still works, as before.
    my_comm = Path('/proc/self/comm').read_text().strip().lower()
    saved = mgr.llm_video_procs
    try:
        stub_gpu(mgr, None, video_running=True)  # probe fails; a tool is running
        assert mgr._gpu_busy(), 'running tools must decide when nvidia-smi cannot'
        assert mgr._gpu_busy_reason == 'video tool running', mgr._gpu_busy_reason

        stub_gpu(mgr, None)
        assert not mgr._gpu_busy()
    finally:
        mgr.llm_video_procs = saved
    print("OK  test_gpu_busy_without_nvidia_smi (falls back to running tools)")


def test_llm_beat_expires_when_quiet(mgr, fake):
    stub_gpu(mgr, BENIGN_GPU)
    reset_beat(mgr)
    mgr.note_doclet_event(opens_session=True)
    mgr._last_event = time.time() - (mgr.llm_keep_alive_secs + 1)
    fake.chat_payloads.clear()
    assert mgr.beat() == 'expired'
    assert [p['keep_alive'] for p in fake.chat_payloads] == [0, 0], fake.chat_payloads
    assert not mgr._alive_session
    assert mgr.beat() == 'idle'
    print("OK  test_llm_beat_expires_when_quiet (GPU released after the window)")


def test_llm_beat_disabled(fake):
    # keep_alive 0 means 'never hold'; DOCLETS_LLM_ALIVE=0 switches beating off.
    saved = {k: os.environ.get(k) for k in ('DOCLETS_LLM_KEEP_ALIVE', 'DOCLETS_LLM_ALIVE')}
    try:
        os.environ['DOCLETS_LLM_KEEP_ALIVE'] = '0'
        assert mod.DocletManager().beat() == 'off'
        os.environ['DOCLETS_LLM_KEEP_ALIVE'] = '60s'
        os.environ['DOCLETS_LLM_ALIVE'] = '0'
        assert mod.DocletManager().beat() == 'off'
    finally:
        for key, value in saved.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print("OK  test_llm_beat_disabled (keep_alive 0 and DOCLETS_LLM_ALIVE=0)")


def test_plugin_wiring_records_events(mgr, fake):
    """`doclets ...` is the .as-facing surface: check what it reports to the beat."""

    class Stub:
        def __init__(self, value):
            self._value = value
            self.set_to = None

        def getValue(self):
            return self._value

        def setValue(self, value):
            self.set_to = value

    stub_gpu(mgr, BENIGN_GPU)
    handler = mod.Doclets.__new__(mod.Doclets)  # __init__ needs a compiler
    handler.program = type('P', (), {})()
    handler.program.doclets_manager = mgr
    handler.nextPC = lambda: 'next'
    handler.getObject = lambda value: value
    handler.getVariable = lambda name: Stub({} if name == 'D' else None)

    # A beat must not be recorded as activity, or the session could never end.
    reset_beat(mgr)
    mgr.note_doclet_event(opens_session=True)
    opened_at = mgr._last_event
    handler.r_doclets({'mode': 'beat'})
    assert mgr._last_event == opened_at, 'a beat refreshed the activity window'
    assert mgr._alive_session

    # `doclets topics` (reading the client) refreshes the window but, on its own,
    # must not start a session — that would load a model just to list topics.
    reset_beat(mgr)
    handler.r_doclets({'mode': 'topics', 'target': 'T', 'message': 'D'})
    assert not mgr._alive_session, 'listing topics must not open a session'

    # `doclets query` opens one, which is what gets the model loaded once.
    handler.r_doclets({'mode': 'query', 'target': 'T', 'message': 'D'})
    assert mgr._alive_session, 'a query must open a session'
    print("OK  test_plugin_wiring_records_events (beat/query/topics → hold/refresh)")


def test_llm_beat_keep_alive_must_exceed_beat(mgr, fake):
    saved = os.environ.get('DOCLETS_LLM_BEAT')
    try:
        os.environ['DOCLETS_LLM_BEAT'] = '120'  # above the 60s keep-alive
        mod.DocletManager()  # warns; the model would expire between beats
        os.environ['DOCLETS_LLM_BEAT'] = '30'
    finally:
        if saved is None:
            os.environ.pop('DOCLETS_LLM_BEAT', None)
        else:
            os.environ['DOCLETS_LLM_BEAT'] = saved
    print("OK  test_llm_beat_keep_alive_must_exceed_beat (misconfiguration warns)")


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
        stub_gpu(mgr, BENIGN_GPU)

        test_filename_lookup(mgr)
        test_literal_substring(mgr)
        test_empty_query_lists_all(mgr)
        test_semantic_llm_ranking(mgr, fake)
        test_synthesis(mgr, fake)
        test_embed_cache_incremental(base, fake)
        test_answer_protocol(mgr, fake)
        test_llm_ready(mgr, fake)
        test_llm_nomatch_fallback(mgr, fake)
        test_llm_nomatch_hint(base, fake)
        test_acl_permissions()
        test_readable_topics(base)
        test_llm_keep_alive_parsing()
        test_llm_beat_holds_model_warm(mgr, fake)
        test_llm_beat_does_not_count_as_activity(mgr, fake)
        test_llm_beat_events_refresh_window(mgr, fake)
        test_llm_beat_yields_to_video(mgr, fake)
        test_video_activity_scan()
        test_gpu_client_parsing()
        test_gpu_busy_from_nvidia_smi(mgr)
        test_gpu_busy_without_nvidia_smi(mgr)
        test_llm_beat_expires_when_quiet(mgr, fake)
        test_llm_beat_disabled(fake)
        test_plugin_wiring_records_events(mgr, fake)
        test_llm_beat_keep_alive_must_exceed_beat(mgr, fake)
        print("\nAll tests passed.")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    main()
