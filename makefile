reformat:
	black --target-version py38 `git ls-files "*.py" "*.pyi"`
stylecheck:
	black --check --target-version py38 `git ls-files "*.py" "*.pyi"`