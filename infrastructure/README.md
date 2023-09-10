# Infrastructure-as-Code for OBC
This is the Infrastructure as Code provisioner for OBC.

To run, first add a LastPass notes entry called obc_credentials that has the following notes field:

    AWS_ACCESS_KEY_ID=ACCESS_KEY
    AWS_SECRET_ACCESS_KEY=SECRET_ACCESS_KEY
    OBC_DB_PASSWORD=THE_DATABASE_PASSWORD
    AWS_DEFAULT_REGION=eu-west-2

ensure you have LastPass CLI installed and can access your vault, then issue:

    . ./setup_creds.sh
    terraform init
    terraform apply

There are then multiple stages of configuration that should be run in order:

    server_setup.sh     # probably only run this once. Called automatically by Terraform
    deploy.sh           # run this whenever you want to trigger a deployment from Github
    migrate.sh          # run this to run database migrations (also part of deploy)

To setup SSL, after the initial server_setup.sh run:

    sudo certbot --nginx -d openbookcollective.org -d www.openbookcollective.org


# Notes
* SSH keys are hardcoded to /home/martin/.ssh/id_ed25519.pub (Martin Eve) and /home/martin/.ssh/andy_2.pub (Andy Byers)
* The ansible portions require ansible galaxy and the community.crypto extension
* Fixtures import creates lock files in the OBC home directory/lock that stops Ansible re-running it in future. Deleting these files and directories will re-import fixtures.
* Terraform is configured, by default, to use remote state. Initial setup of this requires you to remove the S3 backend from main.tf, create the state bucket, and then re-instate the backend. The KMS key has to be copied manually from the outputs because variables/module includes are not allowed in terraform backend configuration blocks.
* To understand the backup system, please see the notes in the backup app.

