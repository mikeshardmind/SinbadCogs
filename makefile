reformat:
	black `git ls-files "*.py"`
stylecheck:
	black --check `git ls-files "*.py"`