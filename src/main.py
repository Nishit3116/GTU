import sys
import os
import json
import logging
import shutil
from pathlib import Path

# Add project root directory to python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from gtu_academic_engine.config import config

def parse_agent_inputs():
    """Parse agent inputs from CLI arguments, environment variables, or stdin JSON."""
    inputs = {}
    
    # 1. Stdin JSON input (common for serverless/agent platforms)
    if not sys.stdin.isatty():
        try:
            stdin_data = sys.stdin.read().strip()
            if stdin_data:
                inputs.update(json.loads(stdin_data))
        except Exception:
            pass
            
    # 2. Environment variables input
    for key in [
        'subject_code', 'course', 'branch', 'branch_name', 'semester', 
        'elective_type', 'academic_year', 'download_type', 
        'start_year', 'end_year', 'session_order', 'merge_order'
    ]:
        env_val = os.environ.get(key.upper())
        if env_val:
            inputs[key] = env_val

    # 3. CLI arguments input (highest priority)
    import argparse
    parser = argparse.ArgumentParser(description="GTU Academic Agent - Automated Downloader & Scraper")
    
    # Input schema fields for the agent
    parser.add_argument("--subject_code", type=str, help="GTU Subject Code (e.g. 3170719, 110001)")
    parser.add_argument("--course", type=str, help="Course ID (e.g. BE, ME, Diploma)")
    parser.add_argument("--branch", type=str, help="Branch ID (e.g. 07 for Computer Engineering)")
    parser.add_argument("--branch_name", type=str, help="Human-readable branch name")
    parser.add_argument("--semester", type=str, help="Semester number (1-8)")
    parser.add_argument("--elective_type", type=str, help="Elective or Non_Elective")
    parser.add_argument("--academic_year", type=str, help="Academic year (e.g. 2024-25)")
    parser.add_argument("--download_type", type=str, default="both", choices=["pyq", "syllabus", "both"], help="What to download: pyq, syllabus, or both")
    parser.add_argument("--start_year", type=int, default=2018, help="Start year for PYQs")
    parser.add_argument("--end_year", type=int, default=2026, help="End year for PYQs")
    parser.add_argument("--session_order", type=str, default="winter-first", choices=["winter-first", "summer-first"], help="Session order (winter-first, summer-first)")
    parser.add_argument("--merge_order", type=str, default="ascending", choices=["ascending", "descending"], help="Merge order (ascending, descending)")
    
    # Server / CLI mode triggers
    parser.add_argument("--server", action="store_true", help="Start the persistent web server instead of a single agent run")
    
    args, unknown = parser.parse_known_args()
    
    # Update inputs with command line values (ignoring defaults first so we don't overwrite stdin/env)
    for k, v in vars(args).items():
        if v is not None and (k == 'server' or v != parser.get_default(k)):
            inputs[k] = v
            
    # Apply defaults for missing inputs
    defaults = {
        "download_type": "both",
        "start_year": 2018,
        "end_year": 2026,
        "session_order": "winter-first",
        "merge_order": "ascending",
        "server": False
    }
    for k, v in defaults.items():
        if k not in inputs:
            inputs[k] = v
            
    return inputs

def run_agent_task(inputs):
    """Execute a single downloader/scraper task and return a JSON result."""
    logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
    logger = logging.getLogger("agent")
    
    subject_code = inputs.get("subject_code")
    if not subject_code:
        print(json.dumps({
            "success": False,
            "error": "Missing required input field: subject_code"
        }, indent=2))
        sys.exit(1)
        
    try:
        # Ensure configuration directories exist
        config.ensure_dirs()
        
        # 1. Resolve subject metadata using cache or live lookup
        from gtu_academic_engine.cache.cache_manager import CacheManager
        cache_manager = CacheManager()
        
        subject = None
        
        # Try resolving from cache
        if cache_manager.has_academic_data():
            logger.info(f"Searching cache for subject code: {subject_code}...")
            cached_subjects = cache_manager.search_subjects(subject_code, top_n=10)
            for cs in cached_subjects:
                if cs.get("subject_code") == subject_code:
                    subject = cs
                    logger.info(f"Resolved subject from cache: {subject.get('subject_name')}")
                    break
                    
        # Try resolving live via Playwright
        if not subject:
            logger.info(f"Subject {subject_code} not resolved from cache. Querying live GTU portal...")
            try:
                from gtu_academic_engine.provider.aspx_provider import ASPXProvider
                with ASPXProvider(headless=True) as prov:
                    scraped = prov.fetch_subject_by_code(subject_code)
                    if scraped:
                        subject = scraped[0]
                        logger.info(f"Resolved subject live: {subject.get('subject_name')}")
            except Exception as exc:
                logger.warning(f"Failed to query live portal for metadata: {exc}")
                
        # Fallback to defaults if metadata couldn't be resolved
        if not subject:
            logger.warning(f"Could not resolve subject metadata. Using default fallback info.")
            subject = {
                "subject_code": str(subject_code),
                "subject_name": str(subject_code),
                "course": inputs.get("course") or "BE",
                "branch": inputs.get("branch") or "07",
                "branch_name": inputs.get("branch_name") or "Computer Engineering",
                "semester": int(inputs["semester"]) if str(inputs.get("semester", "")).isdigit() else 7,
                "elective_type": inputs.get("elective_type") or "Non_Elective",
                "academic_year": inputs.get("academic_year") or "2024-25",
                "semester_label": f"Semester {inputs.get('semester') or 7}"
            }
        else:
            # Overwrite metadata from inputs if they were explicitly provided
            for key in ["course", "branch", "branch_name", "semester", "elective_type", "academic_year"]:
                if inputs.get(key):
                    subject[key] = inputs.get(key)
            if "semester_label" not in subject or inputs.get("semester"):
                subject["semester_label"] = f"Semester {subject.get('semester')}"
                
        # Build structured output directory
        from gtu_academic_engine.downloader.syllabus_downloader import get_structured_output_dir
        out_dir = get_structured_output_dir(subject, config.downloads_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        
        results = {
            "success": True,
            "subject_code": subject_code,
            "subject_name": subject.get("subject_name"),
            "course": subject.get("course"),
            "branch": subject.get("branch_name"),
            "semester": subject.get("semester"),
            "download_type": inputs.get("download_type")
        }
        
        download_type = inputs.get("download_type").lower()
        
        # 1. Download PYQ
        if download_type in ("pyq", "both"):
            try:
                from gtu_pyq_downloader.config import GTUPYQConfig
                from gtu_pyq_downloader.services.pipeline import GTUPYQPipeline
                from gtu_academic_engine.downloader.session_generator import generate_sessions
                
                v1_config = GTUPYQConfig()
                v1_config.downloads_dir = out_dir.parent
                
                sessions = generate_sessions(
                    inputs.get("start_year"), 
                    inputs.get("end_year"), 
                    order=inputs.get("session_order")
                )
                if inputs.get("merge_order") == "ascending":
                    v1_config.sessions = list(reversed(sessions))
                else:
                    v1_config.sessions = sessions
                    
                pipeline = GTUPYQPipeline(v1_config, logger)
                pipeline_result = pipeline.run(subject_code)
                
                results["pyq_success"] = True
                results["pyq_path"] = str(pipeline_result.output_path)
                results["pyq_found"] = pipeline_result.total_found
                results["pyq_missing"] = pipeline_result.total_missing
                
                # Copy merged PYQ PDF to the root directory for easy platform access
                if pipeline_result.output_path and Path(pipeline_result.output_path).exists():
                    root_pyq_path = Path("merged_pyq.pdf")
                    shutil.copy2(pipeline_result.output_path, root_pyq_path)
                    results["merged_pyq_filename"] = str(root_pyq_path)
                    results["merged_pyq_absolute_path"] = str(root_pyq_path.resolve())
                
                pipeline.close()
            except Exception as exc:
                results["pyq_success"] = False
                results["pyq_error"] = str(exc)
                
        # 2. Download Syllabus
        if download_type in ("syllabus", "both"):
            try:
                from gtu_academic_engine.downloader.syllabus_downloader import SyllabusDownloader
                dl = SyllabusDownloader(base_dir=config.downloads_dir)
                saved_path = dl.download(subject)
                if saved_path:
                    results["syllabus_success"] = True
                    results["syllabus_path"] = str(saved_path)
                    
                    # Copy syllabus PDF to the root directory for easy platform access
                    root_syllabus_path = Path("syllabus.pdf")
                    shutil.copy2(saved_path, root_syllabus_path)
                    results["syllabus_filename"] = str(root_syllabus_path)
                    results["syllabus_absolute_path"] = str(root_syllabus_path.resolve())
                else:
                    results["syllabus_success"] = False
                    results["syllabus_error"] = "Syllabus PDF not found on GTU site."
            except Exception as exc:
                results["syllabus_success"] = False
                results["syllabus_error"] = str(exc)
                
        # Output final result JSON
        print(json.dumps(results, indent=2))
        
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e)
        }, indent=2))
        sys.exit(1)

def run_web_server():
    """Start the persistent web server."""
    from gtu_academic_engine.main import run
    os.environ["SERVER_MODE"] = "true"
    run()

if __name__ == "__main__":
    inputs = parse_agent_inputs()
    
    # If explicitly requested web server, or if subject_code is not provided,
    # fallback to starting the web server so they can access the full UI
    if inputs.get("server") or not inputs.get("subject_code"):
        run_web_server()
    else:
        run_agent_task(inputs)
