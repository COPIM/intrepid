FROM python:buster
ADD . /vol/app
WORKDIR /vol/app
RUN pip3 install -r requirements.txt --src /tmp/src
RUN if [ -n "$(ls -A ./lib)" ]; then pip3 install -e lib/*; fi

EXPOSE 8000
STOPSIGNAL SIGINT
ENTRYPOINT ["python", "src/manage.py"]
CMD ["runserver", "0.0.0.0:8000"]
