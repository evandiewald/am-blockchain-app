import gnupg

gpg = gnupg.GPG()
input_data = gpg.gen_key_input(name_real='Test Engineer', name_email='engineer@cmu.edu', passphrase='pw')
key = str(gpg.gen_key(input_data))

print('Test Engineer: \n', key)

input_data = gpg.gen_key_input(name_real='Test Technician', name_email='technician@cmu.edu', passphrase='pw')
key = str(gpg.gen_key(input_data))

print('Test Technician: \n', key)

input_data = gpg.gen_key_input(name_real='Test Admin', name_email='admin@cmu.edu', passphrase='pw')
key = str(gpg.gen_key(input_data))

print('Test Admin: \n', key)



