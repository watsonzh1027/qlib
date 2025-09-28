To update your forked GitHub repository with the latest changes from the original project (the upstream repository), you typically need to perform the following steps:

1.  **Configure the Remote:** Add the original repository as a new **remote** named `upstream`.
2.  **Fetch Changes:** Fetch the branches and their respective commits from the `upstream` repository.
3.  **Merge or Rebase:** Merge the `upstream` changes into your local branch (usually `main` or `master`).

## Step-by-Step Guide

Here's the detailed process using the command line:

### 1\. Configure the Remote for Upstream

First, you need to tell your local copy of the fork about the original repository, which is conventionally called **upstream**.

1.  **Navigate** to your local repository clone in the terminal:

    ```bash
    cd <your-repo-name>
    ```

2.  **Add the upstream remote**. You'll need the URL of the original repository.

    ```bash
    git remote add upstream <original-repo-URL>
    git remote add upstream https://github.com/microsoft/qlib
    ```

    *(Replace `<original-repo-URL>` with the HTTPS or SSH URL of the repository you forked from.)*

3.  **Verify** the new remote configuration:

    ```bash
    git remote -v
    ```

    You should see both your `origin` (your fork) and the new `upstream` (the original project).

-----

### 2\. Fetch the Changes

Next, fetch the changes from the `upstream` remote.

1.  **Fetch** all branches from `upstream`:
    ```bash
    git fetch upstream
    ```
    This downloads the data and branches from the original repository but doesn't merge them into your local files yet.

-----

### 3\. Merge or Rebase

Now that you have the `upstream` changes locally, you can apply them to your working branch (e.g., `main` or `master`).

1.  **Switch** to the branch you want to update (often `main` or `master`):

    ```bash
    git checkout main
    # or git checkout master
    ```

2.  **Merge** the changes from the upstream branch into your current local branch:

    ```bash
    git merge upstream/main
    # or git merge upstream/master
    ```

    This command combines the changes from the original project into your local branch.

      * **Note on Rebasing**: An alternative to `git merge` is `git rebase`, which creates a cleaner, linear history by moving your local commits to the *end* of the upstream changes. If you haven't made local commits yet, or prefer a linear history, use `git rebase upstream/main` instead of `git merge`.

3.  **Resolve Conflicts** (if necessary). If the upstream changes conflict with any changes you've made, Git will prompt you to resolve the merge conflicts manually before the merge/rebase can complete.

-----

### 4\. Push to Your Fork

Finally, you need to push the merged changes from your local repository to your remote fork on GitHub.

1.  **Push** the updated branch to your `origin` (your fork):
    ```bash
    git push origin main
    # or git push origin master
    ```
2. add you to the collaborator list of the repo if needed
Your fork on GitHub is now fully synchronized with the original project.