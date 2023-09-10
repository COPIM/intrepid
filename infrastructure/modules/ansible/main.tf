resource "null_resource" "ansible" {
  provisioner "local-exec" {
    command = "ANSIBLE_HOST_KEY_CHECKING=False ansible-playbook -i ./ansible/hosts.cfg ./ansible/migrate.yml"
  }
  depends_on = [
    local_file.hosts_cfg,
    time_sleep.wait_30_seconds
  ]
}

resource "time_sleep" "wait_30_seconds" {
  create_duration = "30s"
}

resource "local_file" "hosts_cfg" {
  content = templatefile("./templates/hosts.tpl",
    {
      servers     = var.ips
      key         = var.key_name
    }
  )
  filename = "./ansible/hosts.cfg"
}
