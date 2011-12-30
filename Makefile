clean:
	-find -name '*.py[co]' -exec rm '{}' \;
	-test -e test.db && rm test.db
