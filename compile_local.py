import compileall
import os
import shutil
import glob

def compile_project():
    print("Compiling scripts...")
    
    # Create output directory
    dist_dir = "dist_compiled"
    if os.path.exists(dist_dir):
        shutil.rmtree(dist_dir)
    os.makedirs(dist_dir)
    
    # Cleanup previous mess (remove random .pyc and __pycache__)
    print("Cleaning up old compiled files...")
    for root, dirs, files in os.walk('.', topdown=True):
        # Skip venv and dist_compiled
        dirs[:] = [d for d in dirs if d not in ['venv', 'dist_compiled', '.git', '.idea']]
        
        for file in files:
            if file.endswith('.pyc'):
                os.remove(os.path.join(root, file))
        
        if '__pycache__' in dirs:
            shutil.rmtree(os.path.join(root, '__pycache__'))
            dirs.remove('__pycache__')
            
    
    # Move compiled files to dist folder and rename
    # legacy=True creates .pyc files directly next to .py files (Python <3.2 style)
    # But modern python puts them in __pycache__. Let's handle both or just pick one.
    # Actually, compileall.compile_dir(legacy=True) is deprecated/removed in some versions.
    # Safe way: Manual walk
    
    files_to_compile = [
        "config.py",
        "launcher.py", 
        "autobot.py", 
        "autobot2.py", 
        "bot_autogen.py", 
        "auto_hf.py",
        "bot_silverbullet.py",
        "bot_rag.py",
        "bot_super.py"
    ]
    
    import py_compile
    for f in files_to_compile:
        if os.path.exists(f):
            output_name = f + "c" # .py -> .pyc
            target_path = os.path.join(dist_dir, output_name)
            
            print(f"Compiling {f} -> {target_path}")
            py_compile.compile(f, cfile=target_path)
            
    print(f"\n✅ All files compiled to folder: {dist_dir}")

if __name__ == "__main__":
    compile_project()
