reformat:
	black --target-version py38 `git ls-files "*.py"`
stylecheck:
	black --check --target-version py38 `git ls-files "*.py"`