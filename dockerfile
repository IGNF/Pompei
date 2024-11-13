FROM --platform=linux/amd64 ubuntu:focal-20220426

ARG HTTP_PROXY
ENV http_proxy=${HTTP_PROXY}
ENV HTTP_PROXY=${HTTP_PROXY}

ARG HTTPS_PROXY
ENV https_proxy=${HTTPS_PROXY}
ENV HTTPS_PROXY=${HTTPS_PROXY}

ARG NO_PROXY
ENV no_proxy=${NO_PROXY}
ENV NO_PROXY=${NO_PROXY}

ARG CPU
ENV cpu=${CPU}


ARG USER_ID
ENV USER_ID=${USER_ID}


ENV TZ='FR'
ENV DEBIAN_FRONTEND=noninteractive

RUN echo "a"
RUN apt-get update
RUN apt-get install -y python3-pip \
                                git \
                                make \
                                imagemagick \
                                libimage-exiftool-perl \
                                exiv2 \
                                proj-bin \
                                qt5-default \
                                cmake \
                                build-essential \
                                qttools5-dev-tools \
                                exiftool \
                                openbox \
                                parallel \
                                screen \
                                wget \
                                libx11-dev \
                                xorg \
                                openbox \
                                meshlab \
                                vim



#Ajout d'un utilisateur pompei avec le même id que l'utilisateur actuel, pour afficher les interfaces MicMac
RUN useradd -u $USER_ID --shell /bin/bash --create-home pompei && passwd -d pompei
USER pompei

ENV HOME=/home/pompei
WORKDIR $HOME

#Installation de Conda
ENV MAMBA_DIR $HOME/conda
RUN wget --quiet https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh -O ~/miniconda.sh
RUN sh ~/miniconda.sh -b -p $MAMBA_DIR 

ENV PATH=$MAMBA_DIR/bin:$PATH



#Installation de MicMac
RUN git clone https://github.com/micmacIGN/micmac.git
WORKDIR $HOME/micmac
RUN mkdir build
WORKDIR $HOME/micmac/build
RUN  cmake ../
RUN make install -j${cpu}
ENV PATH=$HOME/micmac/bin/:$PATH

#Copie du code Pompei dans l'image
WORKDIR $HOME/pompei
COPY --chown=pompei . .

WORKDIR $HOME/pompei/pompei

#Activation de l'environnement Conda
RUN mamba env create -f environment.yml

RUN mamba init bash

CMD echo "Pompei"