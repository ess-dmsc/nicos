#!/usr/bin/env python3
"""Start_helper: tool for wrapping NICOS scripts into suitable entry points for packaging."""
import sys
import runpy
from pathlib import Path
import nicos

def main():
    """Determine current NICOS script name and run it."""
    # get the name of the script this function was called as (0th argument to
    # argv)
    p = Path(sys.argv[0])
    if p.name == "starter.py":
        # do not call self
        return
    nicos_root = Path(nicos.__file__).parent
    fn = str(nicos_root / 'scripts' / p.name)
    print(f"Starting script {fn}")
    runpy.run_path(fn)

if __name__ == '__main__':
    main()
    
