variable "map_of_instance_data" {
    description = "Map of instance data: {Name = {mysql_cred = value}}}"
    type = map(
            object({
                mysql_username = string
                mysql_password = string
                mysql_database = string
            })
        )
    default = {
        r20240401h0 = {
            mysql_username = "r20240401h0"
            mysql_password = "r20240401h0"
            mysql_database = "r20240401h0"
        },
        r20240401h1 = {
            mysql_username = "r20240401h1"
            mysql_password = "r20240401h1"
            mysql_database = "r20240401h1"
        }
    }
}

variable "prefix" {
  type = string
  default = "distributed_db"
}

variable "az_location" {
  type = string
  default = "westus"
}