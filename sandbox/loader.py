import os

def load_agent_filepaths(directory: str) -> dict:
    """
    Returns a dictionary mapping agent_id -> absolute_filepath
    for all .py files in the given directory.
    """
    agents = {}
    if not os.path.exists(directory):
        return agents
        
    for filename in os.listdir(directory):
        if filename.endswith('.py') and not filename.startswith('__'):
            agent_id = filename[:-3]
            filepath = os.path.abspath(os.path.join(directory, filename))
            agents[agent_id] = filepath
            
    return agents
