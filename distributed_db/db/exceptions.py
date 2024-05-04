class DateOutOfRangeError(Exception):
    def __init__(self, message, date):
        super().__init__(message)
        self.date = date
        
    def __str__(self) -> str:
        return f'DateOutOfRangeError: Invalid Date {self.date} -- {super().__str__()}'


class MetadataDateError(Exception):
    def __init__(self, message, date):
        super().__init__(message)
        self.date = date
    
    def __str__(self) -> str:
        return f'MetadataDateError: Invalid Date {self.date} -- {super().__str__()}' 
    
    
class TerraformError(Exception):
    def __init__(self, message):
        super().__init__(message)
    
    def __str__(self) -> str:
        return f'Terraform Error -- {super().__str__()}'   
    
    
class EmptyMetadataError(Exception):
    def __init__(self, message):
        super().__init__(message)
    
    def __str__(self) -> str:
        return f'EmptyMetadataError: No Metadata -- {super().__str__()}'   
    
class DuplicateDataError(Exception):
    def __init__(self, message):
        super().__init__(message)
    
    def __str__(self) -> str:
        return f'Duplicate Data Error: This key already exists in the database -- {super().__str__()}'   
    