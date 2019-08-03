FROM python:3.7.4-slim-stretch

RUN set -ex; \
  \
  apt update; \
  apt install -y --no-install-recommends \
    cloc \
    curl \
    direnv \
    jq \
    locales \
    make \
    silversearcher-ag \
    tree \
    unzip \
    wget \
    zip; \
  \
  sed -i -e 's/# \(en_US\.UTF-8 .*\)/\1/' /etc/locale.gen; \
  locale-gen en_US.UTF-8; \
  \
  pip install \
    rope; \
  \
  wget -O /vsls https://aka.ms/vsls-linux-prereq-script \
    && sh /vsls \
    && rm -f /vsls; \
  \
  echo 'export PS1="\\w\\$ "' >> /root/.bashrc; \
  echo 'eval "$(direnv hook bash)"' >> /root/.bashrc
 
ENV SHELL /bin/bash
ENV LANG en_US.UTF-8  
ENV LANGUAGE en_US:en  
ENV LC_ALL en_US.UTF-8