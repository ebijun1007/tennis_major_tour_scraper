FROM public.ecr.aws/lambda/python:3.8

RUN pip3 install pandas statsmodels wget sklearn

COPY api.py   ./
CMD ["api.handler"]      