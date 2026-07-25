test:
	./test.sh

clean:
	rm -f *.o *~ tmp*
	rm -rf build

.PHONY: test clean
