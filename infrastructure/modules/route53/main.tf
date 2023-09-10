# Route 53 for domain
resource "aws_route53_zone" "main" {
  name = var.domain_name
}

resource "aws_route53_record" "root-a" {
  zone_id = aws_route53_zone.main.zone_id
  name    = var.domain_name
  type    = "A"
  ttl     = "300"

  records = [var.primary_ip]
}

resource "aws_route53_record" "www-a" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "www.${var.domain_name}"
  type    = "A"
  ttl     = "300"

  records = [var.primary_ip]
}

resource "aws_route53_record" "bookstack" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "bookstack.${var.domain_name}"
  type    = "A"
  ttl     = "300"

  records = ["3.223.136.50"]
}

resource "aws_route53_record" "bookstack_toolkit" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "toolkit.${var.domain_name}"
  type    = "A"
  ttl     = "300"

  records = ["3.223.136.50"]
}

resource "aws_route53_record" "cert_one_javi" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "_7754bee6a1a32098319e75359bade0d6.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"

  records = ["_39f507616d268c4258f185a75d0bf129.fpktwqqglf.acm-validations.aws."]
}


resource "aws_route53_record" "matomo" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "stats.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"

  records = ["wire.reclaimhosting.com"]
}

resource "aws_route53_record" "mailgun_stats" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "email.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"

  records = ["eu.mailgun.org"]
}

resource "aws_route53_record" "office" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "office.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"

  records = ["elb.obpcloud.org"]
}

resource "aws_route53_record" "next_cloud" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "cloud.${var.domain_name}"
  type    = "CNAME"
  ttl     = "300"

  records = ["elb.obpcloud.org"]
}

# zoho verify
resource "aws_route53_record" "root_txt" {
  zone_id = aws_route53_zone.main.zone_id
  name    = ""
  type    = "TXT"
  ttl     = "300"

  records = [
    "zoho-verification=zb19049539.zmverify.zoho.eu",
    "v=spf1 include:zoho.eu include:mailgun.org ~all"
  ]
}

resource "aws_route53_record" "mailgun_verify" {
  zone_id = aws_route53_zone.main.zone_id
  name    = "mta._domainkey.openbookcollective.org"
  type    = "TXT"
  ttl     = "300"

  records = [
    "k=rsa; p=MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDUSO15dx39z8CfOK2Cij3Adxa89htath2wHw8teRWq9PLUSVbRFEQ1v1yM3+OFS9AzrIdF6ZN4iDa8v/4XHbWKr9oBIsC4REfJsMVx7KI1+cf3LIl/bSRBh4mZKvRKj6z2XxRZpaas4rpPEEiC8v+gm4CEP5CLe1yEFhCd6VEtUQIDAQAB",
  ]
}

resource "aws_route53_record" "mx" {
  name    = ""
  type    = "MX"
  zone_id = aws_route53_zone.main.zone_id
  ttl     = "300"
  records = [
    "10 mx.zoho.eu.",
    "20 mx2.zoho.eu.",
    "50 mx3.zoho.eu."
  ]
}
