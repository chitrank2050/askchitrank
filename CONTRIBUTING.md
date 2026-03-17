# Contributing to ML-Notebook-Library

First off, thank you for considering contributing to ML-Notebook-Library! It's people like you that make this such a great community.

## Where do I go from here?

If you've noticed a bug or have a feature request, [make one](https://github.com/chitrank2050/askchitrank/issues/new)! It's generally best if you get confirmation of your bug or approval for your feature request this way before starting to code.

### Fork & create a branch

If this is something you think you can fix, then [fork askchitrank](https://github.com/chitrank2050/askchitrank/fork) and create a branch with a descriptive name.

A good branch name would be (where issue #325 is the ticket you're working on):

```sh
git checkout -b 325-add-japanese-translations
```

### Get the test suite running

Make sure you're on the latest version of the project and that all tests pass.

### Implement your fix or feature

At this point, you're ready to make your changes! Feel free to ask for help; everyone is a beginner at first :smile_cat:

### Make a Pull Request

At this point, you should switch back to your master branch and make sure it's up to date with the latest upstream master.

```sh
git remote add upstream git@github.com:chitrank2050/ML-Notebook-Library.git
git checkout master
git pull upstream master
```

Then update your feature branch from your local copy of master, and push it!

```sh
git checkout 325-add-japanese-translations
git rebase master
git push --force-with-lease origin 325-add-japanese-translations
```

Finally, go to GitHub and make a Pull Request.

## How to report a bug

If you find a security vulnerability, do NOT open an issue. Email us at chitrank2050@gmail.com instead.

In order to determine whether you are dealing with a security issue, ask yourself these two questions:

*   Can I access something that's not mine, or something I shouldn't have access to?
*   Can I disable something for other people?

If the answer to either of those questions is "yes", then you're probably dealing with a security issue. Note that even if you answer "no" to both questions, you may still be dealing with a security issue, so if you're unsure, just email us at chitrank2050@gmail.com.

## How to suggest a feature or enhancement

If you have a great idea for a new feature or an enhancement to an existing one, we'd love to hear about it! Please open an issue on our [GitHub issue tracker](https://github.com/chitrank2050/askchitrank/issues) and we'll be sure to take a look.
