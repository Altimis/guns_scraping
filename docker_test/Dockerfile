FROM public.ecr.aws/bitnami/python:3.8-prod

ADD . /app

RUN pip install pipenv
RUN pipenv install
RUN pip install -r requirements.txt

CMD ["python", "test.py"]