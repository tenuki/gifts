# gifts

An exploratory git-filesystem.

Idea can't be simpler: take a git repository and expose all its branches as directories with their content inside.


## Usage

`$ python gifts.py <source-repo> <mount-point>`


## Example
Suppose you have a repository called Shared, with a README.md file and some release and other branches, you'll see something like this:

```
(env) aweil@pc18:~/.../apath$ ls -la 
drwxrwxr-x  6 aweil aweil 4096 jun 27 12:38 .
drwxrwxr-x 45 aweil aweil 4096 jun 24 20:44 ..
drwxrwxr-x 12 aweil aweil 4096 jun 28 10:22 Shared
drwxrwxr-x 12 aweil aweil 4096 jun 28 10:22 out

(env) aweil@pc18:~/.../apath$ ls -la Shared/
drwxr-xr-x  2 root  root     0 dic 31  1969 .
drwxrwxr-x 12 aweil aweil 4096 jun 29 01:24 ..
drwxrwxr-x 12 aweil aweil 4096 jun 29 01:24 .git
-rw-rw-r-x 12 aweil aweil 4096 jun 29 01:24 README.md

(env) aweil@pc18:~/.../apath$ ls -la out/
drwxr-xr-x  2 root  root     0 dic 31  1969 .
drwxrwxr-x 12 aweil aweil 4096 jun 29 01:24 ..

(env) aweil@pc18:~/.../apath$ python gifts.py ~/.../apath/Shared out

(env) aweil@pc18:~/.../apath$ ls -la out/
drwxr-xr-x  2 root  root     0 dic 31  1969 .
drwxrwxr-x 12 aweil aweil 4096 jun 29 01:24 ..
drwxr-xr-x  2 root  root     0 dic 31  1969 branches

(env) aweil@pc18:~/.../apath$ ls -la out/branches/
drwxr-xr-x 2 root root 0 dic 31  1969 .
drwxr-xr-x 2 root root 0 dic 31  1969 ..
drwxr-xr-x 2 root root 0 dic 31  1969 deploy
drwxr-xr-x 2 root root 0 dic 31  1969 develop
drwxr-xr-x 2 root root 0 dic 31  1969 feature∕someFeature
drwxr-xr-x 2 root root 0 dic 31  1969 fix∕someFix
drwxr-xr-x 2 root root 0 dic 31  1969 HEAD
drwxr-xr-x 2 root root 0 dic 31  1969 master
drwxr-xr-x 2 root root 0 dic 31  1969 release_1.0.0
drwxr-xr-x 2 root root 0 dic 31  1969 release_1.1.0
drwxr-xr-x 2 root root 0 dic 31  1969 release_1.2.0
drwxr-xr-x 2 root root 0 dic 31  1969 release_1.2.1


(env) aweil@pc18:~/.../apath$ find . -type f -iname README.md
./README.md
./out/branches/deploy/README.MD
./out/branches/master/README.md
./out/branches/develop/README.md
./out/branches/release_1.0.0/README.md
./out/branches/release_1.1.0/README.md
...
```
