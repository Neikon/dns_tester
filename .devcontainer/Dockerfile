# Use Fedora 43 to align the development container with the target environment expectations.
FROM registry.fedoraproject.org/fedora:43

# Install system dependencies required for GTK/libadwaita Python development with Meson.
RUN dnf -y update && \
    dnf -y install \
        sudo \
        git \
        bash-completion \
        python3 \
        python3-pip \
        python3-setuptools \
        python3-wheel \
        python3-gobject \
        meson \
        ninja-build \
        pkg-config \
        gcc \
        gcc-c++ \
        make \
        fish \
        gobject-introspection-devel \
        gtk4-devel \
        libadwaita-devel \
        glib2-devel \
        cairo-devel \
        pango-devel \
        desktop-file-utils \
        appstream \
        dbus-daemon \
        which \
        findutils && \
    dnf clean all && rm -rf /var/cache/dnf

# Create a non-root user to avoid developing as root inside the container.
ARG USERNAME=vscode
ARG USER_UID=1000
ARG USER_GID=$USER_UID
RUN groupadd --gid ${USER_GID} ${USERNAME} && \
    useradd -s /bin/bash --uid ${USER_UID} --gid ${USER_GID} -m ${USERNAME} && \
    echo "${USERNAME} ALL=(ALL) NOPASSWD:ALL" > /etc/sudoers.d/${USERNAME} && \
    chmod 0440 /etc/sudoers.d/${USERNAME}

# Set the working directory to the workspace folder used by VS Code devcontainers.
WORKDIR /workspaces
