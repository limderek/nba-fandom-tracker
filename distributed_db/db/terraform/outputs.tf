output "instance_IDs" {
    description = "IDs of each instance"
    value = { for k, v in azurerm_linux_virtual_machine.db_instance : k => v.id }
}

output "public_ips" {
    description = "Public IP addresses of EC2 instances"
    value = { for k, v in azurerm_linux_virtual_machine.db_instance : k => v.public_ip_address }
}