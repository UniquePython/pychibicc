TEST_SRCS=$(filter-out tests/c/common.c, $(wildcard tests/c/*.c))
TESTS=$(patsubst tests/c/%.c, bin/%.exe, $(TEST_SRCS))

bin/%.exe: main.py tests/c/%.c
	mkdir -p build bin
	$(CC) -o- -E -P -C tests/c/$*.c | python3 main.py -o build/$*.s -
	$(CC) -o $@ build/$*.s -xc tests/c/common.c

test: $(TESTS)
	for i in $^; do echo $$i; ./$$i || exit 1; echo; done

clean:
	rm -f *.o *~ tmp*
	rm -rf build bin

.PHONY: test clean
