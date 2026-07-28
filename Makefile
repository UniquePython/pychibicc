test:
	chmod +x ./tests/test_runner.py
	./tests/test_runner.py --full

clean:
	rm -f *.o *~ tmp*
	rm -rf build

.PHONY: test
