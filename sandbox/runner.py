import multiprocessing as mp
import time
import importlib.util
import inspect
from bots.base import Agent

try:
    import psutil
except ImportError:
    psutil = None

def _sandbox_agent_worker(filepath: str, agent_id: str, state: dict, queue: mp.Queue):
    """Worker function that dynamically loads the agent and runs it."""
    try:
        spec = importlib.util.spec_from_file_location(agent_id, filepath)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        
        func = None
        if hasattr(module, 'decide'):
            func = module.decide
        else:
            for name, obj in inspect.getmembers(module):
                if inspect.isclass(obj) and issubclass(obj, Agent) and obj is not Agent:
                    bot_instance = obj()
                    func = bot_instance.decide
                    break
                    
        if func:
            action = func(state)
            queue.put(("SUCCESS", action))
        else:
            queue.put(("ERROR", "No decide function found"))
    except Exception as e:
        queue.put(("ERROR", str(e)))

def run_agent_in_sandbox(filepath: str, agent_id: str, state: dict, timeout: float = 2.0, max_memory_mb: int = 256) -> str:
    """
    Runs an agent's code in a separate process to enforce timeout and memory constraints.
    Filepath is passed so Windows multiprocessing (spawn) avoids pickling issues.
    """
    queue = mp.Queue()
    p = mp.Process(target=_sandbox_agent_worker, args=(filepath, agent_id, state, queue))
    p.start()
    
    start_time = time.time()
    while p.is_alive():
        if time.time() - start_time > timeout:
            p.terminate()
            p.join()
            return "COOPERATE" # Timeout fallback
            
        if psutil is not None:
            try:
                proc = psutil.Process(p.pid)
                mem_info = proc.memory_info()
                if mem_info.rss > max_memory_mb * 1024 * 1024:
                    p.terminate()
                    p.join()
                    return "COOPERATE" # Memory limit fallback
            except psutil.NoSuchProcess:
                pass
                
        time.sleep(0.01)

    p.join()
    
    if not queue.empty():
        status, result = queue.get()
        if status == "SUCCESS":
            return result
            
    return "COOPERATE" # Error fallback
