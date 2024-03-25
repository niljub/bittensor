# Security Checks for Arbitrary Code Execution

### eval() - Executes a string as Python code. Extremely dangerous if used with untrusted input.
```
eval("code_here")
```

### exec() - Executes dynamically created code as Python statements. Similar risks as eval().
```
exec("code_here")
```

### compile() - Compiles source into a code or AST object. Can be used in conjunction with exec() or eval().
```
compile("code_here", "filename", "exec")
```

### __import__() - Used to import modules dynamically. Can be exploited to execute arbitrary code on import.
```
__import__("module_name")
```

### pickle.loads() or pickle.load() - Deserializes byte streams into Python objects. Unsafe if loading pickles from untrusted sources.
```
import pickle
pickle.loads(b"pickle_data")
pickle.load(file_object)
```

### yaml.load() - Without specifying a Loader, it can create arbitrary Python objects. Use yaml.safe_load() instead.
```
import yaml
yaml.load("yaml_data", Loader=yaml.FullLoader) # Unsafe
yaml.safe_load("yaml_data") # Safe
```

### os.system() - Executes the command (a string) in a subshell. Can be used to execute arbitrary system commands.
```
import os
os.system("command_here")
```

### subprocess.Popen(), subprocess.call(), subprocess.run() - Can execute arbitrary commands and scripts if inputs are not validated.
```import subprocess
subprocess.Popen(["command_here"])
subprocess.call(["command_here"])
subprocess.run(["command_here"])
```

### eval() in pandas - pandas.DataFrame.eval() can execute arbitrary strings as code. Use with caution.
```
import pandas as pd
df = pd.DataFrame()
df.eval("expression_here")
```
