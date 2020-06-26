reformat:
	black --target-version py38 `git ls-files "*.py" "*.pyi"`
	isort `git ls-files "*.py" "*.pyi"`
stylecheck:
	black --check --target-version py38 `git ls-files "*.py" "*.pyi"`
	isort --check-only `git ls-files "*.py" "*.pyi"`
