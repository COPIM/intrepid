%{ for index, server in servers ~}
%{ if index == 0 ~}
[wireguardserver]
${server}

[wireguardclients]
%{ else ~}
${server}
%{ endif ~}
%{ endfor ~}

[servers]
%{ for index, server in servers ~}
${server}
%{ endfor ~}

[all:vars]
ansible_ssh_user=ubuntu
ansible_ssh_private_key_file= /home/martin/.ssh/id_ed25519
