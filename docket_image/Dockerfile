FROM python:3.8
#FROM public.ecr.aws/amazonlinux/amazonlinux:2
#FROM amd64/python:3.7

#FROM public.ecr.aws/amazonlinux/amazonlinux:latest

ENV PATH=/usr/local/bin:$PATH \
    LC_ALL=C.UTF-8 \
    LANG=C.UTF-8 \
    WEB_CONCURRENCY=2

# Needed libraries
#RUN DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends apt-utils
#RUN apt-get update && apt-get install -y --no-install-recommends apt-utils
#RUN yum install -y gconf-service
#RUN apt-get update -y


#RUN yum install -y wget xvfb unzip curl

RUN pip install undetected_chromedriver

# Install python 3.7
#RUN yum -y groupinstall "Development Tools"
#RUN yum -y install gcc openssl-devel bzip2-devel libffi-devel
#RUN wget https://www.python.org/ftp/python/3.9.7/Python-3.9.7.tgz
#RUN tar zxvf Python-3.9.7.tgz
#RUN (cd ./Python-3.9.7 && ./configure)
#RUN ls ./Python-3.9.7/
#RUN (cd ./Python-3.9.7/ && make)
#RUN (cd ./Python-3.9.7/ && make altinstall)
#RUN python3.9 --version
#RUN python --version

# Install pip
# uncomment
#RUN python -m pip install -U pip
#RUN python -m pip install -U setuptools

# Set up the Chrome PPA
#RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
#RUN apt-get install -y ./google-chrome-stable_current_*.rpm
# Install Chrome
#RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
#RUN dpkg -i google-chrome-stable_current_amd64.deb; apt-get -fy install

# Install Chrome
#RUN yum install -y google-chrome-stable
#RUN google-chrome-stable --version
#RUN google-chrome --version

#RUN yum install wget
#RUN apt-get update -y
#RUN apt-get install -y unzip xvfb libxi6 libgconf-2-4
#RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_x86_64.rpm
#RUN wget https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
#RUN dpkg -i google-chrome-stable_current_amd64.deb
#RUN apt-get -f install
#RUN apt-get install -y ./google-chrome-stable_current_x86_64.rpm


# Adding trusting keys to apt for repositories

RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add -


# Adding Google Chrome to the repositories

RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'


# Updating apt to see and install Google Chrome

RUN apt-get -y update


# Magic happens

RUN apt-get install -y google-chrome-stable
RUN google-chrome-stable --version



# install google chrome
#RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub
#| apt-key add -
#RUN sh -c 'echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google-chrome.list'
#RUN yum -y update
#RUN yum install -y google-chrome-stable
#RUN curl https://intoli.com/install-google-chrome.sh | bash

# install chromedriver
RUN apt-get install -yqq unzip
RUN wget -O /tmp/chromedriver.zip http://chromedriver.storage.googleapis.com/`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE`/chromedriver_linux64.zip
RUN unzip /tmp/chromedriver.zip chromedriver -d /usr/local/bin/

# set display port to avoid crash
#ENV DISPLAY=:99
EXPOSE 8000
ENV PORT 8000
# workdir
WORKDIR /app

# Copy all data into docker container
COPY . /app
# DO NOT USE YUM AFTER THIS POINT

# Install all pip packages
RUN pip install -r requirements.txt

# Set entrypoint
CMD python app.py