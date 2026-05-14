#!/usr/bin/env python3
"""
Doclet Search and Management for EasyCoder
"""
import sys
import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Tuple, Optional, Any, Union

try:
    import requests
except Exception:
    requests = None

class DocletManager():
    def __init__(self, doclets_dir: str = None, ollama_url: str = "http://localhost:11434"): # type: ignore
        """Initialize the doclet manager
        
        Args:
            doclets_dir: Root directory or comma-separated list of directories containing year folders
            ollama_url: URL of the local Ollama API
        """
        self.set_doclets_dirs(doclets_dir if doclets_dir else "")
        self.ollama_url = ollama_url
        self.model = "llama3.2"  # Default model, can be changed
    
    def set_doclets_dirs(self, doclets_dir: str):
        """Set doclet directories from comma-separated list of paths or topic names.
        
        Handles two formats:
        - Full paths starting with '/': used as-is
        - Topic names (no leading '/'): resolved relative to ~/Doclets/{topic_name}
        """
        self.doclets_dirs = []
        if doclets_dir:
            print(f'Setting the doclet paths to: {doclets_dir}')
            items = [item.strip() for item in doclets_dir.split(',')]
            
            for item in items:
                if item.startswith('/'):
                    # Full path provided
                    path = Path(item).expanduser()
                else:
                    # Topic name provided; resolve to ~/Doclets/{topic_name}
                    path = Path.home() / 'Doclets' / item
                
                self.doclets_dirs.append(path)
                print(f"  Directory {path} exists: {path.exists()}")
        else:
            # Default to ~/Doclets if no input provided
            default_path = Path.home() / 'Doclets'
            self.doclets_dirs = [default_path]
            print(f"  Using default directory {default_path} exists: {default_path.exists()}")
    
    def find_all_doclets(self) -> List[Tuple[Path, str, str]]:
        """Find all doclets in the directory structure
        
        Returns:
            List of tuples: (filepath, filename, subject_line)
        """
        doclets = []
        
        # Search across all configured directories
        for base_dir in self.doclets_dirs:
#            print(f"  Searching in: {base_dir}")
            year_count = 0
            # Look for year folders (e.g., 2026, 2025, etc.)
            for year_folder in base_dir.glob("[0-9][0-9][0-9][0-9]"):
                year_count += 1
                # print(f"    Found year folder: {year_folder.name}")
                if year_folder.is_dir():
                    # Find all .md files in this year folder
                    for doclet_file in year_folder.glob("*.md"):
                        # Read the subject line (first line starting with '# ')
                        try:
                            with open(doclet_file, 'r', encoding='utf-8') as f:
                                first_line = f.readline().strip()
                                subject = first_line[2:].strip() if first_line.startswith('# ') else "No subject"
                                doclets.append((doclet_file, doclet_file.name, subject))
                                # print(f"      Added: {doclet_file.name} - {subject}")
                        except Exception as e:
                            print(f"Warning: Could not read {doclet_file}: {e}", file=sys.stderr)
            if year_count == 0:
                print(f"    No year folders found in {base_dir}")
        return sorted(doclets, key=lambda x: x[1])

    def _get_base_dir_label(self, filepath: Path) -> str:
        """Return the name of the top-level doclets directory for this file."""
        for base_dir in self.doclets_dirs:
            try:
                filepath.relative_to(base_dir)
                return base_dir.name or str(base_dir)
            except ValueError:
                continue
        return ""

    def get_doclet_by_filename(self, name: str) -> Optional[Tuple[Path, str, str]]:
        """Find a single doclet by filename (accepts with/without .md).

        Accepts first-token matching: pass in the leading part of the query
        and we'll normalize to YYMMDD-NN.md.
        """
        token = name.strip()
        # Trim common trailing punctuation from token
        token = token.rstrip(',:;.!')
        # Normalize to filename with .md
        if token.endswith('.md'):
            fname = token
        else:
            fname = f"{token}.md"

        for filepath, filename, subject in self.find_all_doclets():
            if filename == fname:
                return (filepath, filename, subject)
        return None

    def _normalize_display_name(self, display_name: str) -> Optional[str]:
        text = (display_name or '').strip()
        if '/' not in text:
            return None
        topic, filename = text.split('/', 1)
        topic = topic.strip()
        filename = filename.strip()
        if not re.match(r'^[A-Za-z0-9._-]+$', topic):
            return None
        if not re.match(r'^\d{6}-\d{2}\.md$', filename):
            return None
        return f"{topic}/{filename}"

    def _canonical_doclet_path_from_display_name(self, display_name: str) -> Optional[Path]:
        """Map TOPIC/YYMMDD-NN.md to ~/Doclets/TOPIC/20YY/YYMMDD-NN.md."""
        normalized = self._normalize_display_name(display_name)
        if normalized is None:
            return None
        topic, filename = normalized.split('/', 1)
        year = f"20{filename[:2]}"
        return Path.home() / 'Doclets' / topic / year / filename

    def _resolve_display_filename_global(self, display_name: str) -> Optional[Path]:
        """Resolve display filename independent of currently scoped doclet dirs."""
        normalized = self._normalize_display_name(display_name)
        if normalized is None:
            return None

        topic, filename = normalized.split('/', 1)
        year = f"20{filename[:2]}"
        home_doclets = Path.home() / 'Doclets'

        # Exact topic match first.
        exact = home_doclets / topic / year / filename
        if exact.exists():
            return exact

        # Case-insensitive topic match (Linux FS is case-sensitive).
        try:
            for topic_dir in home_doclets.iterdir():
                if topic_dir.is_dir() and topic_dir.name.lower() == topic.lower():
                    candidate = topic_dir / year / filename
                    if candidate.exists():
                        return candidate
        except Exception:
            pass

        # Final fallback: find matching filename in the expected year under any topic.
        try:
            for candidate in home_doclets.glob(f"*/{year}/{filename}"):
                if candidate.exists():
                    return candidate
        except Exception:
            pass
        return None

    def _is_in_home_doclets(self, path: Path) -> bool:
        try:
            path.resolve().relative_to((Path.home() / 'Doclets').resolve())
            return True
        except Exception:
            return False

    def _is_in_doclet_roots(self, path: Path) -> bool:
        try:
            resolved = path.resolve()
        except Exception:
            return False
        for base_dir in self.doclets_dirs:
            try:
                resolved.relative_to(base_dir.resolve())
                return True
            except Exception:
                continue
        return False
    
    def _resolve_display_filename(self, display_name: str) -> Optional[Path]:
        """Resolve a display filename like 'RBR/260102-01.md' back to a Path."""
        normalized = self._normalize_display_name(display_name)
        if normalized is None:
            return None

        # Fast path: canonical storage location. This avoids misses when current
        # search directories are scoped to a subset of topics.
        canonical = self._canonical_doclet_path_from_display_name(normalized)
        if canonical is not None and canonical.exists():
            return canonical

        # Try resolution independent of current scoped search roots.
        global_match = self._resolve_display_filename_global(normalized)
        if global_match is not None:
            return global_match

        for filepath, filename, _subject in self.find_all_doclets():
            disp = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
            if disp == normalized:
                return filepath
        return None

    def read_doclet_content(self, filepath: Union[Path, str]) -> str:
        """Read the full content of a doclet file. Accepts Path, raw path str, or display filename."""
        candidate: Optional[Path] = None

        if isinstance(filepath, Path):
            if filepath.is_absolute() and filepath.exists() and (self._is_in_doclet_roots(filepath) or self._is_in_home_doclets(filepath)):
                candidate = filepath
            else:
                candidate = self._resolve_display_filename(str(filepath))
        else:
            filepath_text = (filepath or '').strip()
            if '/' in filepath_text:
                # Resolve display filename first (e.g., RBR/260102-01.md)
                # to avoid accidental CWD-relative matches.
                normalized = self._normalize_display_name(filepath_text)
                if normalized is not None:
                    candidate = self._resolve_display_filename(normalized)
                    # Brief retry for occasional create->view timing gaps.
                    if candidate is None:
                        for _ in range(10):
                            time.sleep(0.05)
                            candidate = self._resolve_display_filename_global(normalized)
                            if candidate is not None:
                                break
                if candidate is None:
                    path_obj = Path(filepath_text)
                    if path_obj.is_absolute() and path_obj.exists() and (self._is_in_doclet_roots(path_obj) or self._is_in_home_doclets(path_obj)):
                        candidate = path_obj
            else:
                path_obj = Path(filepath_text)
                if path_obj.is_absolute() and path_obj.exists() and (self._is_in_doclet_roots(path_obj) or self._is_in_home_doclets(path_obj)):
                    candidate = path_obj
                else:
                    record = self.get_doclet_by_filename(filepath_text)
                    if record is not None:
                        candidate = record[0]

        if candidate is None:
            return f"Error reading file: could not resolve path for {filepath}"

        try:
            with open(candidate, 'r', encoding='utf-8') as f:
                return f.read()
        except Exception as e:
            return f"Error reading file {candidate}: {e}"

    def _load_save_acl(self, acl_path: Union[Path, str]) -> Dict[str, Any]:
        path = Path(acl_path).expanduser()
        if not path.is_absolute():
            path = (Path.cwd() / path).resolve()
        if not path.exists():
            return {"entries": []}
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if not isinstance(data, dict):
            return {"entries": []}
        if 'entries' not in data or not isinstance(data['entries'], list):
            return {"entries": []}
        return data

    def _resolve_doclet_save_path(self, display_name: str) -> Optional[Path]:
        display_name = self._normalize_display_name(display_name) or ''
        if not display_name:
            return None

        # Existing doclet path
        existing = self._resolve_display_filename(display_name)
        if existing is not None:
            return existing

        # New doclet canonical path.
        return self._canonical_doclet_path_from_display_name(display_name)

    def save_doclet_with_acl(self, payload: str, acl_path: Union[Path, str] = '~/.doclet-save.acl') -> str:
        first_newline = payload.find('\n')
        if first_newline < 0:
            return 'Save failed: invalid payload'

        token = payload[:first_newline].strip()
        remainder = payload[first_newline + 1:]
        second_newline = remainder.find('\n')
        if second_newline < 0:
            return 'Save failed: invalid payload'

        doclet_name = remainder[:second_newline].strip()
        normalized_doclet_name = self._normalize_display_name(doclet_name)
        if normalized_doclet_name is None:
            return 'Save failed: invalid doclet name'
        doclet_name = normalized_doclet_name
        doclet_content = remainder[second_newline + 1:]

        if '/' not in doclet_name:
            return 'Save failed: invalid doclet name'
        topic = doclet_name.split('/', 1)[0]

        acl = self._load_save_acl(acl_path)
        entries = acl.get('entries', [])
        allowed = False
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get('token') != token:
                continue
            topics = entry.get('topics', [])
            if isinstance(topics, list) and ('*' in topics or topic in topics):
                allowed = True
                break

        if not allowed:
            return 'Save failed: unauthorized'

        save_path = self._resolve_doclet_save_path(doclet_name)
        if save_path is None:
            return 'Save failed: invalid doclet name'

        try:
            save_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_path, 'w', encoding='utf-8') as f:
                f.write(doclet_content)
            return f'Saved {doclet_name}'
        except Exception:
            return f'Save failed for {doclet_name}'

    def _is_token_allowed_for_topic(self, token: str, topic: str, acl_path: Union[Path, str] = '~/.doclet-save.acl') -> bool:
        acl = self._load_save_acl(acl_path)
        entries = acl.get('entries', [])
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if entry.get('token') != token:
                continue
            topics = entry.get('topics', [])
            if isinstance(topics, list) and ('*' in topics or topic in topics):
                return True
        return False

    def create_new_doclet(self, topic: str) -> str:
        topic = (topic or '').strip()
        if not re.match(r'^[A-Za-z0-9._-]+$', topic):
            return 'Create failed: invalid topic'

        now = datetime.now()
        yy = now.strftime('%y')
        yyyymmdd = now.strftime('%y%m%d')
        year_dir = Path.home() / 'Doclets' / topic / f'20{yy}'

        try:
            year_dir.mkdir(parents=True, exist_ok=True)
        except Exception:
            return 'Create failed: could not create folder'

        max_seq = -1
        for candidate in year_dir.glob(f'{yyyymmdd}-*.md'):
            match = re.match(rf'^{yyyymmdd}-(\d\d)\.md$', candidate.name)
            if match:
                seq = int(match.group(1))
                if seq > max_seq:
                    max_seq = seq

        next_seq = max_seq + 1
        while next_seq <= 99:
            filename = f'{yyyymmdd}-{next_seq:02d}.md'
            path = year_dir / filename
            if not path.exists():
                break
            next_seq += 1

        if next_seq > 99:
            return 'Create failed: too many doclets for today'

        filename = f'{yyyymmdd}-{next_seq:02d}.md'
        path = year_dir / filename
        display_name = f'{topic}/{filename}'
        default_content = '# New doclet\n'

        try:
            with open(path, 'x', encoding='utf-8') as f:
                f.write(default_content)
            return f'Created {display_name}'
        except FileExistsError:
            return 'Create failed: filename collision, retry'
        except Exception:
            return f'Create failed for {display_name}'

    def create_new_doclet_with_acl(self, payload: str, acl_path: Union[Path, str] = '~/.doclet-save.acl') -> str:
        first_newline = payload.find('\n')
        if first_newline < 0:
            return 'Create failed: invalid payload'

        token = payload[:first_newline].strip()
        remainder = payload[first_newline + 1:]
        second_newline = remainder.find('\n')
        if second_newline < 0:
            topic = remainder.strip()
            request_id = ''
        else:
            topic = remainder[:second_newline].strip()
            request_id = remainder[second_newline + 1:].strip()

        if not topic:
            return 'Create failed: invalid topic'

        if request_id and not re.match(r'^[A-Za-z0-9._-]{1,64}$', request_id):
            request_id = ''

        if not self._is_token_allowed_for_topic(token, topic, acl_path):
            return 'Create failed: unauthorized'

        stamp_path: Optional[Path] = None
        has_stamp_lock = False
        if request_id:
            now = datetime.now()
            yy = now.strftime('%y')
            yyyymmdd = now.strftime('%y%m%d')
            year_dir = Path.home() / 'Doclets' / topic / f'20{yy}'
            try:
                year_dir.mkdir(parents=True, exist_ok=True)
            except Exception:
                return 'Create failed: could not create folder'

            stamp_path = year_dir / f'.newreq-{yyyymmdd}-{request_id}'
            try:
                with open(stamp_path, 'x', encoding='utf-8') as f:
                    f.write('PENDING\n')
                has_stamp_lock = True
            except FileExistsError:
                has_stamp_lock = False

            if not has_stamp_lock:
                for _ in range(20):
                    try:
                        text = stamp_path.read_text(encoding='utf-8').strip()
                    except Exception:
                        text = ''
                    if text.startswith('Created '):
                        display_name = text.replace('Created ', '', 1).strip()
                        expected_path = self._resolve_doclet_save_path(display_name)
                        if expected_path is not None and expected_path.exists():
                            return f'Created {display_name}'
                    time.sleep(0.1)
                return 'Create failed: request busy, retry'

        result = self.create_new_doclet(topic)
        if stamp_path is not None and has_stamp_lock:
            if result.startswith('Created '):
                try:
                    stamp_path.write_text(result + '\n', encoding='utf-8')
                except Exception:
                    pass
            else:
                try:
                    stamp_path.unlink()
                except Exception:
                    pass

        return result

    def delete_doclet_with_acl(self, payload: str, acl_path: Union[Path, str] = '~/.doclet-save.acl') -> str:
        first_newline = payload.find('\n')
        if first_newline < 0:
            return 'Delete failed: invalid payload'

        token = payload[:first_newline].strip()
        doclet_name = payload[first_newline + 1:].strip()
        normalized_doclet_name = self._normalize_display_name(doclet_name)
        if normalized_doclet_name is None:
            return 'Delete failed: invalid doclet name'
        doclet_name = normalized_doclet_name

        if '/' not in doclet_name:
            return 'Delete failed: invalid doclet name'
        topic = doclet_name.split('/', 1)[0]

        if not self._is_token_allowed_for_topic(token, topic, acl_path):
            return 'Delete failed: unauthorized'

        target = self._resolve_display_filename(doclet_name)
        if target is None:
            return 'Delete failed: invalid doclet name'

        try:
            target.unlink()
            return f'Deleted {doclet_name}'
        except FileNotFoundError:
            return f'Delete failed: not found {doclet_name}'
        except Exception:
            return f'Delete failed for {doclet_name}'
    
    def build_search_context(self, doclets: List[Tuple[Path, str, str]]) -> str:
        """Build a context string for the LLM with all doclet metadata
        
        Args:
            doclets: List of (filepath, filename, subject) tuples
            
        Returns:
            Formatted string with doclet information
        """
        context_parts = ["Available doclets:\n"]
        for filepath, filename, subject in doclets:
            context_parts.append(f"- {filename}: {subject}")
        
        return "\n".join(context_parts)
    
    def query_llm(self, prompt: str, model: str = None) -> str: # type: ignore
        """Query the local Ollama LLM
        
        Args:
            prompt: The prompt to send to the LLM
            model: Model name (defaults to self.model)
            
        Returns:
            Response text from the LLM
        """
        if model is None:
            model = self.model

        if requests is None:
            return "Error querying LLM: requests is not installed"
            
        try:
            response = requests.post(
                f"{self.ollama_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            return result.get('response', '').strip()
        except requests.exceptions.RequestException as e:
            return f"Error querying LLM: {e}"
    
    def _match_doclets(self, query: str, use_llm: bool = False) -> Tuple[List[Tuple[Path, str, str]], Optional[str], Dict[str, Any]]:
        """Return matching doclets, optional error code, and metadata."""
#        print(f"_match_doclets called with query: '{query}', use_llm: {use_llm}")
        doclets = self.find_all_doclets()
        meta: Dict[str, Any] = {
            "doclet_count": len(doclets),
            "use_llm": use_llm,
            "match_count": 0,
            "matched_by": None,
            "status": None,
        }
        if use_llm: 
            print("Using LLM for doclet search")

        if not doclets:
            meta["status"] = "no_doclets"
            return [], "no_doclets", meta

        qraw = query.strip()
        qnorm = qraw.strip('"\'')  # tolerate quoted queries
        query_lower = qnorm.lower()
        if not query_lower:
            meta["status"] = "empty_query"
            return [], "empty_query", meta

        # Direct match: display filename (e.g., 'RBR/260102-00.md')
        if '/' in qnorm:
            filepath = self._resolve_display_filename(qnorm)
            if filepath:
                for fpath, fname, subject in doclets:
                    if fpath == filepath:
                        deterministic_matches = [(fpath, fname, subject)]
                        meta["match_count"] = 1
                        meta["matched_by"] = "display_filename"
                        meta["status"] = "ok"
                        return deterministic_matches, None, meta

        # Direct match: bare filename (e.g., '260102-00.md' or '260102-00')
        token = qnorm.rstrip(',:;.!')
        token_fname = token.split('/')[-1]
        if re.match(r"^\d{6}-\d{2}(\.md)?$", token_fname):
            fname = token_fname if token_fname.endswith('.md') else f"{token_fname}.md"
            for fpath, fname_actual, subject in doclets:
                if fname_actual == fname:
                    deterministic_matches = [(fpath, fname_actual, subject)]
                    meta["match_count"] = 1
                    meta["matched_by"] = "filename"
                    meta["status"] = "ok"
                    return deterministic_matches, None, meta
        
        # Deterministic subject+body substring match
        deterministic_matches = []
        for filepath, fname, subject in doclets:
            subj_lower = subject.lower()
            body_lower = self.read_doclet_content(filepath).lower()
            haystack = subj_lower + "\n" + body_lower
            if query_lower in haystack:
                deterministic_matches.append((filepath, fname, subject))

        llm_matches = []
        if use_llm:
            # Two-stage search: Use deterministic matches as pre-filter
            # This limits what gets sent to LLM, saving memory and tokens
            candidate_pool = deterministic_matches if deterministic_matches else doclets
            
            # Limit to top 20 candidates to avoid overwhelming the LLM
            max_candidates = 20
            if len(candidate_pool) > max_candidates:
                candidate_pool = candidate_pool[:max_candidates]
                print(f"[LLM] Pre-filtered to {max_candidates} candidates from {len(doclets)} total doclets")
            
            print(f"[LLM] Invoking LLM for query: '{query}' with {len(candidate_pool)} candidates")
            entries = []
            for filepath, fname, subject in candidate_pool:
                body = self.read_doclet_content(filepath)
                preview = body[:400].replace('\n', ' ')
                entries.append(f"- {fname} | subject: {subject} | preview: {preview}")

            context = "\n".join(entries)
            prompt = f"""You are a precise doclet search helper.
Below is a list of doclets in the format: filename | subject | preview

User query: {query}

IMPORTANT: Return ONLY the exact filenames from the list that match the query.
Filenames follow the format YYMMDD-NN.md (e.g., 260102-00.md).
Handle typos and semantic matches.
Return one filename per line.
If no matches, return: NO_MATCHES

Available doclets:
{context}

Return matching filenames:"""

            llm_response = self.query_llm(prompt)
            print(f"[LLM] Response: {llm_response}")
            if "NO_MATCHES" not in llm_response:
                for line in llm_response.strip().split('\n'):
                    line = line.strip()
                    # Skip empty lines or explanatory text
                    if not line or not re.search(r'\d{6}-\d{2}', line):
                        continue
                    # Extract filename pattern from the line
                    match = re.search(r'(\d{6}-\d{2}(?:\.md)?)', line)
                    if match:
                        fname = match.group(1)
                        if not fname.endswith('.md'):
                            fname = f"{fname}.md"
                    else:
                        continue
                    for fp, f, subj in candidate_pool:
                        if f == fname:
                            llm_matches.append((fp, f, subj))
                            break

        matching_files = llm_matches if use_llm and llm_matches else deterministic_matches

        meta["match_count"] = len(matching_files)
        meta["matched_by"] = "llm" if use_llm and llm_matches else "deterministic"

        if not matching_files:
            meta["status"] = "no_matches"
            return [], "no_matches", meta

        meta["status"] = "ok"
        return matching_files, None, meta

    def search_data(self, query: str, include_content: bool = False, use_llm: bool = False, include_summary: bool = False, return_meta: bool = False) -> Union[List[Dict[str, Any]], Tuple[List[Dict[str, Any]], Dict[str, Any]]]:
        """Programmatic search returning raw data; optionally include metadata."""
        # print(f"search_data called with query: '{query}'")
        
        # Force content when query is clearly a path or filename (allow quoted inputs)
        qtrim = query.strip()
        qnorm = qtrim.strip('"\'')
        is_display_filename_query = '/' in qnorm
        fname_token = qnorm.rstrip(',:;.!').split('/')[-1]
        is_filename_query = bool(re.match(r"^\d{6}-\d{2}(\.md)?$", fname_token))
        include_content_final = include_content or is_display_filename_query or is_filename_query
        
        matches, error, meta = self._match_doclets(query=query, use_llm=use_llm)
        # print(f"  _match_doclets returned: error={error}, match_count={meta.get('match_count')}, status={meta.get('status')}")

        results: List[Dict[str, Any]] = []
        if not error:
            for filepath, filename, subject in matches:
                entry: Dict[str, Any] = {
                    "filepath": filepath,
                    "filename": filename,
                    "display_filename": f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename,
                    "subject": subject,
                }

                content: Optional[str] = None
                if include_content_final or include_summary:
                    content = self.read_doclet_content(filepath)

                if include_content_final and content is not None:
                    entry["content"] = content

                if include_summary and content is not None:
                    snippet_raw = content.strip().replace('\n', ' ')
                    entry["summary"] = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw

                results.append(entry)

        if return_meta:
            meta["results_included"] = bool(results)
            return results, meta

        return results

    def search(self, query: str, include_content: bool = False, use_llm: bool = False, include_summary: bool = False) -> str:
        """Search doclets using deterministic matching, optional LLM rerank/semantic."""
        # Fast-path: when listing contents, allow direct filename access
        if include_content:
            first_token = re.split(r"\s+", query.strip(), maxsplit=1)[0] if query.strip() else ""
            # Match YYMMDD-NN optionally with .md
            if re.match(r"^\d{6}-\d{2}(\.md)?$", first_token):
                record = self.get_doclet_by_filename(first_token)
                if record:
                    filepath, filename, subject = record
                    display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
                    content = self.read_doclet_content(filepath)
                    snippet = None
                    if include_summary:
                        snippet_raw = content.strip().replace('\n', ' ')
                        snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                    block_lines = [f"{'='*70}", f"File: {display_name}", f"Subject: {subject}"]
                    if snippet:
                        block_lines.append(f"Summary: {snippet}")
                    block_lines.append(f"{'='*70}")
                    block_lines.append(content)
                    block_lines.append(f"{'='*70}")
                    return "\n".join(block_lines)

        matches, error, _meta = self._match_doclets(query=query, use_llm=use_llm)

        if error == "no_doclets":
            return "No doclets found in the directory structure."
        if error == "empty_query":
            return "Please provide a search query."
        if error == "no_matches":
            return "No matching doclets found for your query."

        result_parts = [f"Found {len(matches)} matching doclet{'s' if len(matches) != 1 else ''}:\n"]
        for filepath, filename, subject in matches:
            display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
            if include_content:
                content = self.read_doclet_content(filepath)
                snippet = None
                if include_summary:
                    snippet_raw = content.strip().replace('\n', ' ')
                    snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                block_lines = [f"{'='*70}", f"File: {display_name}", f"Subject: {subject}"]
                if snippet:
                    block_lines.append(f"Summary: {snippet}")
                block_lines.append(f"{'='*70}")
                block_lines.append(content)
                block_lines.append(f"{'='*70}")
                result_parts.append("\n".join(block_lines))
            else:
                if include_summary:
                    body = self.read_doclet_content(filepath)
                    snippet_raw = body.strip().replace('\n', ' ')
                    snippet = (snippet_raw[:240] + '…') if len(snippet_raw) > 240 else snippet_raw
                    result_parts.append(f"- {display_name}: {subject}\n  summary: {snippet}")
                else:
                    result_parts.append(f"- {display_name}: {subject}")

        return "\n".join(result_parts)
    
    def list_all(self, verbose: bool = False) -> str:
        """List all doclets with their subjects
        
        Args:
            verbose: If True, include full content of each doclet
        """
        doclets = self.find_all_doclets()
        
        if not doclets:
            return "No doclets found."
        
        result = [f"Total: {len(doclets)} doclets\n"]
        
        # Group by year
        by_year = {}
        for filepath, filename, subject in doclets:
            year = filepath.parent.name
            if year not in by_year:
                by_year[year] = []
            by_year[year].append((filepath, filename, subject))
        
        for year in sorted(by_year.keys(), reverse=True):
            result.append(f"\n{year}:")
            for filepath, filename, subject in by_year[year]:
                display_name = f"{self._get_base_dir_label(filepath)}/{filename}" if self._get_base_dir_label(filepath) else filename
                if verbose:
                    # Show full content
                    content = self.read_doclet_content(filepath)
                    result.append(f"\n{'='*70}")
                    result.append(f"File: {display_name}")
                    result.append(f"Subject: {subject}")
                    result.append(f"{'='*70}")
                    result.append(content)
                    result.append(f"{'='*70}\n")
                else:
                    # Just filename and subject
                    result.append(f"  - {display_name}: {subject}")
        
        return "\n".join(result)

###############################################################################
###############################################################################
# The Doclets compiler and runtime handlers

from easycoder import Handler, ECValue, ECDictionary, ECList, ECVariable

class Doclets(Handler):

    def __init__(self, compiler):
        super().__init__(compiler)
        self.spoke = None
        print(f"Doclets handler initialized from {__file__}")

    def getName(self):
        return 'doclets'

    #############################################################################
    # Keyword handlers

    def k_doclets(self, command):
        mode = self.peek()
        if mode == 'init':
            self.nextToken()
            self.add(command)
            return True
        if mode in ('query', 'view', 'save', 'new', 'delete'):
            self.nextToken()
            command['mode'] = mode
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                if mode == 'query':
                    self.checkObjectType(record, ECList)
                else:
                    self.checkObjectType(record, ECVariable)
                command['target'] = record['name']
                self.skip('from')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECDictionary())
                    command['message'] = record['name']
                    self.add(command)
                    return True
        return False
    
    def r_doclets(self, command):
        if 'mode' in command:
            if not hasattr(self.program, 'doclets_manager'):
                raise RuntimeError(self.program, 'Doclets manager not initialized')

            mode = command['mode']
            target = self.getObject(self.getVariable(command['target']))
            message = self.getObject(self.getVariable(command['message'])).getValue()
            results = ''

            if mode == 'query':
                query = message.get('message', '')
                if isinstance(query, bytes):
                    query = query.decode('utf-8', errors='replace')
                p = query.find('|')
                topics = query[:p] if p != -1 else ''
                query = query[p+1:] if p != -1 else ''

                if topics:
                    self.program.doclets_manager.set_doclets_dirs(topics)

                use_llm = False
                if query.startswith('LLM:'):
                    use_llm = True
                    query = query[4:].strip()

                print(f'query: {query}, topics: {topics}, use_llm: {use_llm}')

                results = self.program.doclets_manager.search_data(
                    query=query,
                    include_content=False,
                    use_llm=use_llm,
                    include_summary=False,
                    return_meta=False
                )

                topics_dict = {}
                for r in results:
                    display_name = r.get('display_filename', '') # type: ignore
                    topic = display_name.split('/')[0].lower() if '/' in display_name else display_name.lower()
                    if topic not in topics_dict:
                        topics_dict[topic] = []
                    topics_dict[topic].append(r)

                sorted_results = []
                for topic in sorted(topics_dict.keys()):
                    topic_group = sorted(topics_dict[topic], key=lambda r: r.get('filename', ''), reverse=True)
                    sorted_results.extend(topic_group)
                results = sorted_results

                res = []
                for r in results:
                    if 'content' in r:
                        res.append(r.get('content')) # type: ignore
                    else:
                        display_name = r.get('display_filename', '')
                        subject = r.get('subject', '')
                        res.append(f"{display_name}: {subject}") # type: ignore
                results = res

            elif mode == 'view':
                results = self.program.doclets_manager.read_doclet_content(message['message'])

            elif mode == 'save':
                payload = message.get('message', '')
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8', errors='replace')
                results = self.program.doclets_manager.save_doclet_with_acl(payload)

            elif mode == 'new':
                payload = message.get('message', '')
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8', errors='replace')
                results = self.program.doclets_manager.create_new_doclet_with_acl(payload)

            elif mode == 'delete':
                payload = message.get('message', '')
                if isinstance(payload, bytes):
                    payload = payload.decode('utf-8', errors='replace')
                results = self.program.doclets_manager.delete_doclet_with_acl(payload)

            if isinstance(results, str):
                results = ECValue(type=str, content=results)
            elif isinstance(results, list):
                results = ECValue(type=list, content=results)
            target.setValue(results)
            return self.nextPC()

        # Use default ollama_url if not provided
        ollama_url = command.get('ollama_url', 'http://localhost:11434')
        doclets_manager = DocletManager(
            doclets_dir=command.get('doclets_dir'),
            ollama_url=ollama_url
        )
        self.program.doclets_manager = doclets_manager
        return self.nextPC()

    # get doclet {list} from {message}
    def k_get(self, command):
        if self.nextIs('doclet'):
            if self.nextIsSymbol():
                record = self.getSymbolRecord()
                self.checkObjectType(record, ECList)
                command['target'] = record['name']
                self.skip('from')
                if self.nextIsSymbol():
                    record = self.getSymbolRecord()
                    self.checkObjectType(record, ECDictionary())
                    command['message'] = record['name']
                    self.add(command)
                    return True
        return False
    
    def r_get(self, command):
        if not hasattr(self.program, 'doclets_manager'):
            raise RuntimeError(self.program, 'Doclets manager not initialized')
        target = self.getObject(self.getVariable(command['target']))
        message = self.getObject(self.getVariable(command['message'])).getValue()
        results = ''
        
        action = message.get('action', '')
        
        # Normalize incoming fields to UTF-8 strings
        query = message.get('message', '')
#        print(query)
        if isinstance(query, bytes):
            query = query.decode('utf-8', errors='replace')
        
        if action == 'query':
            p = query.find('|')
            topics = query[:p] if p != -1 else ''
            query = query[p+1:] if p != -1 else ''

            # Extract topics and set doclet directories
            if topics:
                self.program.doclets_manager.set_doclets_dirs(topics)
            
            # Extract message and check for LLM prefix
            use_llm = False
            if query.startswith('LLM:'):
                use_llm = True
                query = query[4:].strip()  # Remove 'LLM:' prefix and trim whitespace
            
            print(f'query: {query}, topics: {topics}, use_llm: {use_llm}')
            
            # Perform search
            results = self.program.doclets_manager.search_data(
                query=query,
                include_content=False,
                use_llm=use_llm,
                include_summary=False,
                return_meta=False
            )
            
            # Sort by topic first, then by filename within each topic
            # First pass: group results by topic
            topics_dict = {}
            for r in results:
                display_name = r.get('display_filename', '') # type: ignore
                topic = display_name.split('/')[0].lower() if '/' in display_name else display_name.lower()
                if topic not in topics_dict:
                    topics_dict[topic] = []
                topics_dict[topic].append(r)
            
            # Second pass: sort each topic group by filename, then combine in topic order
            sorted_results = []
            for topic in sorted(topics_dict.keys()):
                topic_group = sorted(topics_dict[topic], key=lambda r: r.get('filename', ''), reverse=True)
                sorted_results.extend(topic_group)
            results = sorted_results
            
            # Format results: append subject to display filename
            res = []
            for r in results:
                if 'content' in r:
                    res.append(r.get('content')) # type: ignore
                else:
                    # Append subject to display filename
                    display_name = r.get('display_filename', '')
                    subject = r.get('subject', '')
                    res.append(f"{display_name}: {subject}") # type: ignore
            results = res

        elif action == 'view':
            # Extract doclet name
            # doclet_name = message.get('name', '')
            # if isinstance(doclet_name, bytes):
            #     doclet_name = doclet_name.decode('utf-8', errors='replace')
            # if not doclet_name:
            #     raise RuntimeError(self.program, "No 'name' provided for view action")
            # Read doclet content directly by name
            results = self.program.doclets_manager.read_doclet_content(message['message'])
        elif action == 'save':
            payload = message.get('message', '')
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8', errors='replace')
            results = self.program.doclets_manager.save_doclet_with_acl(payload)
        elif action == 'new':
            payload = message.get('message', '')
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8', errors='replace')
            results = self.program.doclets_manager.create_new_doclet_with_acl(payload)
        elif action == 'delete':
            payload = message.get('message', '')
            if isinstance(payload, bytes):
                payload = payload.decode('utf-8', errors='replace')
            results = self.program.doclets_manager.delete_doclet_with_acl(payload)
        else:
            results = f'Error: unsupported doclets action "{action}"'
        
        # Convert results to ECValue
        if isinstance(results, str):
            results = ECValue(type=str, content=results)
        elif isinstance(results, list):
            results = ECValue(type=list, content=results)
        target.setValue(results)
        return self.nextPC()

    #############################################################################
    # Compile a value in this domain
    def compileValue(self):
        value = ECValue(domain=self.getName())
        token = self.getToken()
        if token == 'the':
            token = self.nextToken()
        if token == 'doclet':
            token = self.nextToken()
            if token == 'topics':
                value.setType('topics')
                return value
        return None

    #############################################################################
    # Modify a value or leave it unchanged.
    def modifyValue(self, value):
        return value

    #############################################################################
    # Value handlers

    def v_message(self, v):
        return self.program.mqttClient.getMessagePayload()

    def v_topic(self, v):
        return self.program.mqttClient.getMessageTopic()
    
    def v_topics(self, v):
        # Return list of directories in ~/Doclets
        doclets_root = Path.home() / 'Doclets'
        if doclets_root.exists() and doclets_root.is_dir():
            topics = [d.name for d in doclets_root.iterdir() if d.is_dir() and d.name[0] != '.']
            return sorted(topics)
        return []

    #############################################################################
    # Compile a condition
    def compileCondition(self):
        condition = {}
        return condition

    #############################################################################
    # Condition handlers
