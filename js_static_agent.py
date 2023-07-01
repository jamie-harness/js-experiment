import glob
import os
import subprocess
import threading
import time

globs = ["**/*.test.tsx", "**/*.test.ts"]
# globs = ["/src/modules/75-ce/utils/__test__/utils.test.tsx"]
exclude_list = ["react", "moment"]
glob_cache = {}
# globs = ["pandas/testing.py"]
tests = []

visited = {}

parents = {}

cwd = os.getcwd()

lock = threading.Lock()

thread_max = 16


def DFS(path_to_file):

    global visited  
    global parents
    global lock
    global glob_cache

    path_to_file = os.path.abspath(path_to_file)
    # result = []
    if not (path_to_file.endswith(".tsx") or path_to_file.endswith(".ts") or path_to_file.endswith(".js")):
        return
    with lock:
        if path_to_file in visited or path_to_file == "":
            return
        visited[path_to_file] = []
    # print(path_to_file)
    # print(threading.active_count())
    with open(path_to_file, "r") as file:
        bracketFrom = ''
        commentStart = False
        for line in file:
            line = line.strip()
            tokens = line.split(" ")
            if commentStart and "*/" not in line:
                continue
            elif "*/" in line and "/*" in line:
                continue
            # elif bracketFrom != '':
            #     if line.endswith(")"):
            #         bracketFrom = ""
            #     for token in tokens:
            #         if token == ")":
            #             break
            #         childFiles = findFileName(bracketFrom + "."+ token.strip(","))
            #         # visited[path_to_file].extend(childFiles)
            #         for childFile in childFiles:
            #             if childFile in parents:
            #                 if path_to_file not in parents[childFile]:
            #                     parents[childFile].append(path_to_file)
            #             else:
            #                 parents[childFile] = [path_to_file]
            #             DFS(childFile)
            #             # result.extend(childResult)
            #             # visited[path_to_file].extend(childResult)
            #     continue
            elif line.startswith("from") or line.startswith("import"):
                if ("from" in line):
                    from_start = False
                    for token in tokens:
                        if token == "from":
                            from_start = True
                        elif from_start:
                            childFiles = findFileName(token, path_to_file)
                            # visited[path_to_file].extend(childFiles)
                            if threading.active_count() < thread_max * 2:
                                threads = [None] * len(childFiles)
                                for i, childFile in enumerate(childFiles):
                                    with lock:
                                        if childFile in parents:
                                            if path_to_file not in parents[childFile]:
                                                parents[childFile].append(path_to_file)
                                        else:
                                            parents[childFile] = [path_to_file]
                                    threads[i] = threading.Thread(target=DFS, args=([childFile]))
                                    threads[i].start()
                                for i in range(len(childFiles)):
                                    threads[i].join()
                            else:
                                for childFile in childFiles:
                                    with lock:
                                        if childFile in parents:
                                            if path_to_file not in parents[childFile]:
                                                parents[childFile].append(path_to_file)
                                        else:
                                            parents[childFile] = [path_to_file]
                                    DFS(childFile)
                        # result.extend(childResult)
                        # visited[path_to_file].extend(childResult)
            # elif (line.startswith("from")):
            #     if len(tokens) > 1:
            #         childFiles = findFileName(tokens[1])
            #         # visited[path_to_file].extend(childFiles)
            #         for childFile in childFiles:
            #             if childFile in parents:
            #                 if path_to_file not in parents[childFile]:
            #                     parents[childFile].append(path_to_file)
            #             else:
            #                 parents[childFile] = [path_to_file]
            #             DFS(childFile)
            #             # result.extend(childResult)
            #             # visited[path_to_file].extend(childResult)
            elif (len(tokens)) == 0:
                continue
            elif line == "":
                continue
            elif line.startswith("//"):
                continue
            elif line.startswith('/*'):
                commentStart = True
                continue
            elif '*/' in line:
                commentStart = False
                continue
            else:
                continue
    # return result


def findFileName(importStr, pwd):
    global glob_cache
    # print("//")
    # print(importStr)
    importStr = importStr.strip("'")
    pwd = os.path.dirname(os.path.realpath(pwd))
    flist = []
    if importStr.startswith("@"):
        path = importStr.strip("@")
        flist = glob.glob("**" + path + "*", recursive=True)
        return flist
    if importStr == "": 
        return []
    splits = importStr.split('/')
    count = 0
    for split in splits:
        if split == "..":
            count = count + 1


    abs_path = False
    
    if count != 0:
        pwd = "/".join(pwd.split("/")[0:-count])
    elif importStr.startswith("./"):
        importStr = importStr[2:]
    elif not importStr.startswith("/"):
        abs_path = True
    element = splits[-1]
    if abs_path:
        if importStr not in exclude_list:
            if importStr not in glob_cache:
                flist = glob.glob("**/" + importStr + "*", recursive=True, root_dir=cwd)
                with lock:
                    glob_cache[importStr] = flist
            else:
                flist = glob_cache[importStr]
    else:
        flist = glob.glob("**" + element + "*", recursive=True, root_dir=pwd)
    final_list = []
    for file in flist:
        if "node_module" not in file:
            if abs_path:
                final_list.append(cwd + "/" + file)
            else: 
                final_list.append(pwd + "/" + file)

    return final_list

startts = time.time()

for g in globs:
    tests.extend(glob.glob(g, recursive=True))

print(len(tests))

i = 0
while i < len(tests):
    j = 0
    root_threads = [None] * thread_max
    while j < thread_max:
        if (i * thread_max + j < len(tests)):
            root_threads[j] = threading.Thread(target=DFS, args=([tests[i * thread_max + j]]))
            root_threads[j].start()
        j =  j + 1
    j = 0
    while j < thread_max:
        if (i * thread_max + j < len(tests)):
            root_threads[j].join()
        j =  j + 1
    i = i + 1

# for i in range(len(tests)):
#     root_threads[i].join()

# for k,v in visited.items():
#     # final = []
#     for i in v:
#         if i in parents:
#             if k not in parents[i]:
#                 parents[i].append(k)
#         else:
#             parents[i] = [k]
    
#     visited[k] = list(dict.fromkeys(v))
# print(visited)
# print(parents)

res = []
cmd_result = subprocess.check_output(["git diff --name-status --diff-filter=MADR HEAD@{1} HEAD -1"], shell=True, text=True)
# cmd_result = subprocess.check_output(["git diff --name-status"], shell=True, text=True)
for l in cmd_result.splitlines():
    t = l.split()
    if len(t) == 0:
        break
    if  t[0][0]== 'M':
        res.append(t[1])
    elif t[0][0] == 'A':
        res.append(t[1])
    elif t[0][0] == 'D':
        res.append(t[1])
    elif t[0][0] == 'R':
        res.append(t[1])
        res.append(t[2])

selection = []
for change in res:
    change = os.path.abspath(change)
    if change in parents:
        selection.extend(parents.get(change))

print(selection)
print(time.time()-startts)
        
