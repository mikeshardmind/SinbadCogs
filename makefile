reformat:
	black -N `git ls-files "*.py"`
stylecheck:
	black --check -N `git ls-files "*.py"`