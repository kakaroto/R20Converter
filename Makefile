
windows:
	rm -rf windows
	python setup.py py2exe

release: all windows

clean:
	rm -rf *~ */*~ src/*.pyc windows/


.PHONY: windows
