### Add submodule to project
```
cd path/to/project/submodules
git submodule add [URL to Git repo]
```

### Clone with submodules
```
git clone --recursive [URL to Git repo] 
```

### Pull all changes in the repo including changes in the submodules
```
git pull --recurse-submodules
```

### Pull all changes for the submodules
```
git submodule update --remote
```

### When making changes in the submodules please commit them first:
```
# So, first commit/push your submodule's changes:
cd path/to/submodule
git add <stuff>
git commit -m "comment"
git push
# Then, update your main project to track the updated version of the submodule:
cd /main/project
git add path/to/submodule
git commit -m "updated my submodule"
git push
```