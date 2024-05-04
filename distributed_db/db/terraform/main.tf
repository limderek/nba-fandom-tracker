terraform {
  required_providers {
    azurerm = {
      source = "hashicorp/azurerm"
      version = "3.96.0"
    }
  }
}

provider "azurerm" {
  # Configuration options
  features {
     resource_group {
       prevent_deletion_if_contains_resources = false
     }
 }
}

resource "tls_private_key" "private_key" {
  algorithm = "RSA"
  rsa_bits = 4096
}

resource "local_file" "private_key_local" {
  content          = tls_private_key.private_key.private_key_pem
  filename         = "${path.module}/ssh/azureskey.pem"
  file_permission  = "0400"  
  directory_permission = "0700"
}

resource "azurerm_resource_group" "distributed_db_rg" {
  name     = "${var.prefix}-rg"
  location = var.az_location
}

resource "azurerm_virtual_network" "distributed_db_vn" {
  name                = "${var.prefix}-vn"
  address_space       = ["10.0.0.0/16"]
  location            = azurerm_resource_group.distributed_db_rg.location
  resource_group_name = azurerm_resource_group.distributed_db_rg.name
}

resource "azurerm_subnet" "distributed_db_subnet" {
  name                 = "${var.prefix}-subnet"
  resource_group_name  = azurerm_resource_group.distributed_db_rg.name
  virtual_network_name = azurerm_virtual_network.distributed_db_vn.name
  address_prefixes     = ["10.0.2.0/24"]
}

resource "azurerm_network_security_group" "distributed_db_nsg" {
  name                = "distributed_db_nsg"
  location            = azurerm_resource_group.distributed_db_rg.location
  resource_group_name  = azurerm_resource_group.distributed_db_rg.name
}

resource "azurerm_network_security_rule" "ssh" {
 name                        = "AllowSSH"
 priority                    = 1001
 direction                   = "Inbound"
 access                      = "Allow"
 protocol                    = "Tcp"
 source_port_range           = "*"
 destination_port_range      = "22"
 source_address_prefix       = "*"
 destination_address_prefix = "*"
 resource_group_name  = azurerm_resource_group.distributed_db_rg.name
 network_security_group_name = azurerm_network_security_group.distributed_db_nsg.name
}

resource "azurerm_network_security_rule" "mysql" {
 name                        = "AllowMySQL"
 priority                    = 1002
 direction                   = "Inbound"
 access                      = "Allow"
 protocol                    = "Tcp"
 source_port_range           = "*"
 destination_port_range      = "3306"
 source_address_prefix       = "*"
 destination_address_prefix  = "*"
 resource_group_name         = azurerm_resource_group.distributed_db_rg.name
 network_security_group_name = azurerm_network_security_group.distributed_db_nsg.name
}

resource "azurerm_public_ip" "db_instance_public_ip" {
  for_each = var.map_of_instance_data

  name = "${each.key}-public-ip"
  location = azurerm_resource_group.distributed_db_rg.location
  resource_group_name = azurerm_resource_group.distributed_db_rg.name
  allocation_method = "Dynamic"
}

resource "azurerm_network_interface" "distributed_db_ni" {
  for_each = var.map_of_instance_data

  name = "${each.key}-ni"
  location = azurerm_resource_group.distributed_db_rg.location
  resource_group_name = azurerm_resource_group.distributed_db_rg.name

  ip_configuration {
    name = "ip"
    subnet_id = azurerm_subnet.distributed_db_subnet.id
    private_ip_address_allocation = "Dynamic"
    public_ip_address_id          = azurerm_public_ip.db_instance_public_ip[each.key].id
  }

  depends_on = [ azurerm_public_ip.db_instance_public_ip ]
}

resource "azurerm_linux_virtual_machine" "db_instance" {
  for_each = var.map_of_instance_data

  name                = each.key
  resource_group_name = azurerm_resource_group.distributed_db_rg.name
  location            = azurerm_resource_group.distributed_db_rg.location
  size                = "Standard_B1s"
  admin_username      = "dsci551"
  network_interface_ids = [azurerm_network_interface.distributed_db_ni[each.key].id]
  

  admin_ssh_key {
    username   = "dsci551"
    public_key = tls_private_key.private_key.public_key_openssh
 }

 os_disk {
    caching              = "ReadWrite"
    storage_account_type = "Standard_LRS"
 }

 source_image_reference {
    publisher = "Canonical"
    offer     = "0001-com-ubuntu-server-focal"
    sku       = "20_04-lts-gen2"
    version   = "latest"
 }

 custom_data = base64encode(templatefile("${path.module}/scripts/init_mysql.sh", {
     MYSQL_USERNAME = each.value.mysql_username
     MYSQL_PASSWORD = each.value.mysql_password
     MYSQL_DATABASE = each.value.mysql_database
 }))

 tags = {
     Name = each.key
 }

 depends_on = [ azurerm_network_interface.distributed_db_ni ]
}


