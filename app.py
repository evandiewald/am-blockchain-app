from tkinter import Tk, Label, Button, Entry, messagebox, OptionMenu, StringVar, ttk, filedialog
import blockchain
import os
import smart_contract
import mysql.connector
import time
import datetime
import pickle

cnx = mysql.connector.connect(user='node0', password='pw', host='127.0.0.1', database='amb')


class blockchainApp:
    def __init__(self, master, platform):
        if platform is "RPi":
            import RPi.GPIO as GPIO
            from mfrc522 import SimpleMFRC522

            reader = SimpleMFRC522()
            self.material_lot_id = []


        self.platform = platform
        self.user_email = []
        self.user_pw = []
        self.user_role = []
        self.register_window = []
        self.app_window = []
        self.tab_parent = []
        self.overview_tab = []
        self.new_project_tab = []
        self.load_project_tab = []
        self.resources_tab = []
        self.listBox_overview_myprojects = []
        self.listBox_overview_recentblocks = []
        self.browse_filename = []
        self.blockchain = blockchain.BlockchainConnection(cnx)

        #
        self.project_window = []
        self.project_overview_label = []
        self.var_project_name = []
        self.var_current_state = []
        self.var_latest_update = []
        self.var_technician_email = []
        self.technician_email = []

        #
        self.listBox_deploy_project = []
        self.listBox_submit_powder = []
        self.listBox_build_report = []
        self.listBox_post_processing = []
        self.listBox_invoice = []

        self.master = master
        master.title("AM Blockchain")

        self.welcome_label = Label(master, text="Welcome to AM Blockchain! Please login with your GPG credentials")
        self.welcome_label.grid(row=0, column=1)

        self.email_label = Label(master, text="Email address")
        self.email_label.grid(row=1, column=0)

        self.email_login = Entry(master)
        self.email_login.grid(row=1, column=1)

        self.pw_label = Label(master, text="Password")
        self.pw_label.grid(row=2, column=0)

        self.pw_login = Entry(master)
        self.pw_login.grid(row=2, column=1)

        self.login_button = Button(master, text="Login", command=self.login)
        self.login_button.grid(row=3, column=2)

        self.register_button = Button(master, text="New User", command=self.register)
        self.register_button.grid(row=3, column=3)

    def read_rfid_tag(self):
        messagebox.showinfo('Place your tag near the RFID scanner to read')
        try:
            scan_id, self.material_lot_id = reader.read()
            disp_message = "Powder Logged successfully with Lot ID: " + self.material_lot_id
            messagebox.showinfo(disp_message)
        finally:
            GPIO.cleanup()

    def browse(self):
        file = filedialog.askopenfile(parent=self.app_window, mode='rb', title='Choose a file')
        self.browse_filename = file.name
        messagebox.showinfo('File selected', message=['File selected: '+ self.browse_filename])

    def submit_new_contract(self, project_name, technician_email, oracle_string, comments):
        if self.browse_filename is not None:
            filename = os.path.basename(self.browse_filename)
            build_file_hash = blockchain.encrypt_and_upload_file(self.blockchain, self.browse_filename,
                                                                 recipients=[self.user_email, technician_email])
            contract = smart_contract.SmartContract(self.blockchain, str(self.user_role))
            contract.deploy_contract(project_name, self.user_email, self.user_email, technician_email, technician_email,
                                     filename, build_file_hash, comments, oracle_string)
            self.refresh_page()
            self.browse_filename = []
        else:
            messagebox.showerror('Error', 'No file selected!')

    def submit_powder(self, contract_id, powder_id):
        contract = smart_contract.SmartContract(self.blockchain, str(self.user_role), contract_id=contract_id)
        contract.submit_powder(powder_id)
        self.refresh_project(contract_id)
        self.refresh_transactions(contract_id)
        if self.platform is 'RPi':
            self.material_lot_id = []

    def submit_build_report(self, contract_id):
        if self.browse_filename is not None:
            filename = os.path.basename(self.browse_filename)
            build_file_hash = blockchain.encrypt_and_upload_file(self.blockchain, self.browse_filename,
                                                                 recipients=[self.user_email,
                                                                             self.technician_email])
            contract = smart_contract.SmartContract(self.blockchain, str(self.user_role), contract_id)
            contract.submit_build_report(filename, build_file_hash)
            self.refresh_project(contract_id)
            self.refresh_transactions(contract_id)
            self.browse_filename = []
        else:
            messagebox.showerror('Error', 'No file selected!')

    def submit_post_processing(self, contract_id, post_processing_procedure):
        contract = smart_contract.SmartContract(self.blockchain, str(self.user_role), contract_id=contract_id)
        contract.submit_post_processing_procedure(post_processing_procedure)
        self.refresh_project(contract_id)
        self.refresh_transactions(contract_id)

    def submit_invoice(self, contract_id):
        if self.browse_filename is not None:
            filename = os.path.basename(self.browse_filename)
            build_file_hash = blockchain.encrypt_and_upload_file(self.blockchain, self.browse_filename,
                                                                 recipients=[self.user_email,
                                                                             self.technician_email])
            contract = smart_contract.SmartContract(self.blockchain, str(self.user_role), contract_id)
            contract.submit_build_report(filename, build_file_hash)
            self.refresh_project(contract_id)
            self.refresh_transactions(contract_id)
            self.browse_filename = []
        else:
            messagebox.showerror('Error', 'No file selected!')

    def download_file(self, contract_id, file_hash, file_name):
        blockchain.decrypt_and_download_file(self.blockchain, file_hash, contract_id, file_name, gpg_pw='pw')
        messagebox.showinfo('Decryption successful', message=['File downloaded and decrypted successfully: ' + file_name])

    def refresh_page(self):
        # overview tab
        self.blockchain = blockchain.BlockchainConnection(cnx)
        mycontracts = blockchain.find_my_contracts(self.blockchain.cnx, self.user_email)
        self.listBox_overview_myprojects.delete(*self.listBox_overview_myprojects.get_children())
        for row in range(len(mycontracts['deployed_timestamp'])):
            self.listBox_overview_myprojects.insert("", "end", values=(
                mycontracts['deployed_timestamp'][row], mycontracts['contract_id'][row],
                mycontracts['project_name'][row],
                mycontracts['engineer_email'][row], mycontracts['technician_email'][row],
                mycontracts['update_timestamp'][row], mycontracts['current_state'][row]))

        recent_blocks = blockchain.read_last_few_blocks(self.blockchain, 5)
        self.listBox_overview_recentblocks.delete(*self.listBox_overview_recentblocks.get_children())
        for row in range(5):
            self.listBox_overview_recentblocks.insert("", "end", values=(
                recent_blocks[1][row], recent_blocks[2][row], recent_blocks[4][row], recent_blocks[3][row]))

    def refresh_project(self, contract_id):
        self.refresh_page()
        contract_header = blockchain.download_contract_header(self.blockchain.cnx, contract_id)
        self.var_project_name = StringVar()
        self.var_project_name.set('Project Name: ' + contract_header['project_name'])
        self.var_technician_email = StringVar()
        self.var_technician_email.set('Technician Email: ' + contract_header['technician_email'])
        self.technician_email = contract_header['technician_email']
        self.var_latest_update = StringVar()
        ts = time.mktime(
            datetime.datetime.strptime(contract_header['last_update_timestamp'], "%Y_%m_%d %H_%M_%S").timetuple())
        self.var_latest_update.set('Last Update Timestamp: ' + str(time.ctime(ts)))
        self.var_current_state = StringVar()
        self.var_current_state.set('Current State: ' + contract_header['current_state'])
        self.project_window.update_idletasks()

    def refresh_transactions(self, contract_id):
        transaction_paths = blockchain.read_my_transactions(self.blockchain, contract_id, gpg_pw='pw')
        for i in range(len(transaction_paths)):
            txn_state = os.path.basename(transaction_paths[i])
            transaction_data = pickle.load(open(transaction_paths[i], "rb"))
            if txn_state == 'Contract Submitted':
                self.listBox_deploy_project.delete(*self.listBox_deploy_project.get_children())
                self.listBox_deploy_project.insert("", "end", values=(
                    transaction_data['transaction_timestamp'], transaction_data['filename'],
                    transaction_data['build_file_hash'][0], transaction_data['comments'],
                    transaction_data['oracle_string']))
            elif txn_state == 'Powder Selected':
                self.listBox_submit_powder.delete(*self.listBox_submit_powder.get_children())
                self.listBox_submit_powder.insert("", "end", values=(
                    transaction_data['transaction_timestamp'], transaction_data['powder_id']))
            elif txn_state == 'Build Report Submitted':
                self.listBox_build_report.delete(*self.listBox_build_report.get_children())
                self.listBox_build_report.insert("", "end", values=(
                    transaction_data['transaction_timestamp'], transaction_data['filename'],
                    transaction_data['build_report_hash'][0]))
            elif txn_state == 'Post Processing Submitted':
                self.listBox_post_processing.delete(*self.listBox_post_processing.get_children())
                self.listBox_post_processing.insert("", "end", values=(
                    transaction_data['transaction_timestamp'], transaction_data['post_processing_procedure']))
            elif txn_state == 'Invoice Submitted':
                self.listBox_invoice.delete(*self.listBox_invoice.get_children())
                self.listBox_invoice.insert("", "end", values=(
                    transaction_data['transaction_timestamp'], transaction_data['filename'],
                    transaction_data['invoice_hash'][0]))
            else:
                raise NameError('Unknown State Name')
        self.project_window.update_idletasks()

    def app_window_setup(self):
        self.app_window = Tk()
        self.app_window.title("AM Blockchain - Homepage")
        self.tab_parent = ttk.Notebook(self.app_window)
        self.tab_parent.grid()
        self.overview_tab = ttk.Frame(self.app_window)
        self.new_project_tab = ttk.Frame(self.app_window)
        self.resources_tab = ttk.Frame(self.app_window)

        self.tab_parent.add(self.overview_tab, text="Overview")
        self.tab_parent.add(self.new_project_tab, text="New Project")
        self.tab_parent.add(self.resources_tab, text="Resources")

        # overview tab
        welcome_text = "Welcome, " + self.user_email + " (" + self.user_role + ", Carnegie Mellon Additive Lab)"
        welcome_text_label = Label(self.overview_tab, text=welcome_text)
        welcome_text_label.grid(row=0, column=0, columnspan=3)

        listBox_overview_myprojects_label = Label(self.overview_tab, text="My Projects")
        listBox_overview_myprojects_label.grid(row=1, column=0)

        cols_overview_myprojects = (
            'Deployed', 'Contract ID', 'Project Name', 'Engineer Email', 'Technician Email', 'Last Update',
            'Current State')
        self.listBox_overview_myprojects = ttk.Treeview(self.overview_tab, columns=cols_overview_myprojects,
                                                        show='headings')
        for col in cols_overview_myprojects:
            self.listBox_overview_myprojects.heading(col, text=col)
        self.listBox_overview_myprojects.grid(row=2, column=0, columnspan=3)

        def open_my_project(a):
            curItem = self.listBox_overview_myprojects.focus()
            contract_id = self.listBox_overview_myprojects.item(curItem)['values'][1]
            contract_id = str(contract_id).zfill(3)
            self.open_project(contract_id)

        self.listBox_overview_myprojects.bind('<Double-1>', open_my_project)

        listBox_overview_recentblocks_label = Label(self.overview_tab, text="Recent Blocks")
        listBox_overview_recentblocks_label.grid(row=3, column=0)

        cols_overview_recentblocks = ('Index', 'Timestamp', 'Transaction Hash', 'Previous Block Hash')
        self.listBox_overview_recentblocks = ttk.Treeview(self.overview_tab, columns=cols_overview_recentblocks,
                                                          show='headings')
        for col in cols_overview_recentblocks:
            self.listBox_overview_recentblocks.heading(col, text=col)
        self.listBox_overview_recentblocks.grid(row=4, column=0, columnspan=3)

        # new projects tab
        new_project_label = Label(self.new_project_tab, text='New Project')
        new_project_label.grid(row=0, column=0, columnspan=3)

        new_project_name_label = Label(self.new_project_tab, text='Project Name')
        new_project_name_label.grid(row=1, column=0)

        new_project_name_entry = Entry(self.new_project_tab)
        new_project_name_entry.grid(row=1, column=1)

        new_project_tech_label = Label(self.new_project_tab, text='Technician Email')
        new_project_tech_label.grid(row=2, column=0)

        new_project_tech_entry = Entry(self.new_project_tab)
        new_project_tech_entry.grid(row=2, column=1)

        new_project_file_label = Label(self.new_project_tab, text='Choose Build File')
        new_project_file_label.grid(row=3, column=0)

        new_project_file_button = Button(self.new_project_tab, text='Browse', command=self.browse)
        new_project_file_button.grid(row=3, column=1)

        new_project_oracle_label = Label(self.new_project_tab, text='Oracle String')
        new_project_oracle_label.grid(row=4, column=0)

        new_project_oracle_entry = Entry(self.new_project_tab)
        new_project_oracle_entry.grid(row=4, column=1)

        new_project_comments_label = Label(self.new_project_tab, text='Comments')
        new_project_comments_label.grid(row=5, column=0)

        new_project_comments_entry = Entry(self.new_project_tab)
        new_project_comments_entry.grid(row=5, column=1)

        new_project_submit_button = Button(self.new_project_tab, text='Submit',
                                           command=lambda: self.submit_new_contract(new_project_name_entry.get(),
                                                                                    new_project_tech_entry.get(),
                                                                                    new_project_oracle_entry.get(),
                                                                                    new_project_comments_entry.get()))
        new_project_submit_button.grid(row=6, column=2)

        # resources tab

        self.refresh_page()

    def open_project(self, contract_id):
        self.project_window = Tk()
        self.project_window.title("Project Window")
        self.project_tab_parent = ttk.Notebook(self.project_window)
        self.project_tab_parent.grid()
        self.project_overview_tab = ttk.Frame(self.project_window)
        self.powder_selection_tab = ttk.Frame(self.project_window)
        self.build_report_tab = ttk.Frame(self.project_window)
        self.post_processing_tab = ttk.Frame(self.project_window)
        self.invoice_tab = ttk.Frame(self.project_window)

        self.project_tab_parent.add(self.project_overview_tab, text="Project Overview")
        self.project_tab_parent.add(self.powder_selection_tab, text="Powder Selection")
        self.project_tab_parent.add(self.build_report_tab, text="Build Report")
        self.project_tab_parent.add(self.post_processing_tab, text="Post Processing")
        self.project_tab_parent.add(self.invoice_tab, text="Invoice")

        self.refresh_project(contract_id)

        # overview tab
        self.project_overview_label = Label(self.project_overview_tab, text='Project Overview')
        self.project_overview_label.grid(row=1, column=1, columnspan=3)

        self.project_name_label = Label(self.project_overview_tab, text=self.var_project_name.get())
        self.project_name_label.grid(row=2, column=1)

        self.technician_email_label = Label(self.project_overview_tab, text=self.var_technician_email.get())
        self.project_name_label.grid(row=3, column=1)

        self.latest_update_label = Label(self.project_overview_tab, text=self.var_latest_update.get())
        self.latest_update_label.grid(row=4, column=1)

        self.current_state_label = Label(self.project_overview_tab, text=self.var_current_state.get())
        self.current_state_label.grid(row=5, column=1)

        # transaction listboxes
        # deploy
        listBox_deploy_project_label = Label(self.project_overview_tab, text="Build File(s) and Comments")
        listBox_deploy_project_label.grid(row=6, column=1)

        cols_deploy_project = ('Timestamp', 'Filename', 'Build File IPFS Hash', 'Comments', 'Oracle String')
        self.listBox_deploy_project = ttk.Treeview(self.project_overview_tab, columns=cols_deploy_project,
                                                   show='headings', height=2)
        for col in cols_deploy_project:
            self.listBox_deploy_project.heading(col, text=col)
        self.listBox_deploy_project.grid(row=7, column=0, columnspan=3)

        def download_build_file(a):
            curItem = self.listBox_deploy_project.focus()
            file_hash = self.listBox_deploy_project.item(curItem)['values'][2]
            file_name = self.listBox_deploy_project.item(curItem)['values'][1]
            self.download_file(contract_id, file_hash, file_name)
        self.listBox_deploy_project.bind('<Double-1>', download_build_file)

        # powder
        listBox_submit_powder_label = Label(self.project_overview_tab, text="Powder Selection")
        listBox_submit_powder_label.grid(row=8, column=1)

        cols_submit_powder = ('Timestamp', 'Powder ID')
        self.listBox_submit_powder = ttk.Treeview(self.project_overview_tab, columns=cols_submit_powder,
                                                  show='headings', height=2)
        for col in cols_submit_powder:
            self.listBox_submit_powder.heading(col, text=col)
        self.listBox_submit_powder.grid(row=9, column=0, columnspan=3)

        # build report
        listBox_build_report_label = Label(self.project_overview_tab, text="Build Report")
        listBox_build_report_label.grid(row=10, column=1)

        cols_build_report = ('Timestamp', 'Filename', 'Build Report IPFS Hash')
        self.listBox_build_report = ttk.Treeview(self.project_overview_tab, columns=cols_build_report,
                                                 show='headings', height=2)
        for col in cols_build_report:
            self.listBox_build_report.heading(col, text=col)
        self.listBox_build_report.grid(row=11, column=0, columnspan=3)

        def download_build_report(a):
            curItem = self.listBox_build_report.focus()
            file_hash = self.listBox_build_report.item(curItem)['values'][2]
            file_name = self.listBox_build_report.item(curItem)['values'][1]
            self.download_file(contract_id, file_hash, file_name)
        self.listBox_build_report.bind('<Double-1>', download_build_report)

        # post processing
        listBox_post_processing_label = Label(self.project_overview_tab, text="Post Processing Procedure")
        listBox_post_processing_label.grid(row=12, column=1)

        cols_post_processing = ('Timestamp', 'Post Processing Procedure')
        self.listBox_post_processing = ttk.Treeview(self.project_overview_tab, columns=cols_post_processing,
                                                    show='headings', height=2)
        for col in cols_post_processing:
            self.listBox_post_processing.heading(col, text=col)
        self.listBox_post_processing.grid(row=13, column=0, columnspan=3)

        # invoice
        listBox_invoice_label = Label(self.project_overview_tab, text="Invoice")
        listBox_invoice_label.grid(row=14, column=1)

        cols_invoice = ('Timestamp', 'Filename', 'Invoice IPFS Hash')
        self.listBox_invoice = ttk.Treeview(self.project_overview_tab, columns=cols_invoice, show='headings', height=2)
        for col in cols_invoice:
            self.listBox_invoice.heading(col, text=col)
        self.listBox_invoice.grid(row=15, column=0, columnspan=3)

        def download_invoice(a):
            curItem = self.listBox_invoice.focus()
            file_hash = self.listBox_invoice.item(curItem)['values'][2]
            file_name = self.listBox_invoice.item(curItem)['values'][1]
            self.download_file(contract_id, file_hash, file_name)
        self.listBox_invoice.bind('<Double-1>', download_invoice)

        self.refresh_transactions(contract_id)
        self.project_window.update_idletasks()

        # contract functions
        # powder selection tab
        powder_label = Label(self.powder_selection_tab, text='Powder Selection')
        powder_label.grid(row=0, column=0, columnspan=3)

        powder_id_label = Label(self.powder_selection_tab, text='Powder ID')
        powder_id_label.grid(row=1, column=0)

        if self.platform == 'RPi':
            powder_scan_button = Button(self.powder_selection_tab, command=self.read_rfid_tag)
            powder_scan_button.grid(row=1, column=1)
            powder_submit_button = Button(self.powder_selection_tab, text='Submit',
                                          command=lambda: self.submit_powder(contract_id, self.material_lot_id))
            powder_submit_button.grid(row=2, column=2)
        else:
            powder_id_entry = Entry(self.powder_selection_tab)
            powder_id_entry.grid(row=1, column=1)
            powder_submit_button = Button(self.powder_selection_tab, text='Submit',
                                          command=lambda: self.submit_powder(contract_id, powder_id_entry.get()))
            powder_submit_button.grid(row=2, column=2)

        # build report tab
        build_report_label = Label(self.build_report_tab, text='Submit Build Report')
        build_report_label.grid(row=0, column=0, columnspan=3)

        build_report_file_label = Label(self.build_report_tab, text='Choose Build Report File')
        build_report_file_label.grid(row=1, column=0)

        build_report_file_button = Button(self.build_report_tab, text='Browse', command=self.browse)
        build_report_file_button.grid(row=1, column=1)

        build_report_submit_button = Button(self.build_report_tab, text='Submit',
                                            command=lambda: self.submit_build_report(contract_id))
        build_report_submit_button.grid(row=2, column=2)

        # post processing tab
        post_processing_label = Label(self.post_processing_tab, text='Post Processing Procedure')
        post_processing_label.grid(row=0, column=0, columnspan=3)

        post_processing_entry_label = Label(self.post_processing_tab, text='Procedure')
        post_processing_entry_label.grid(row=1, column=0)

        post_processing_entry = Entry(self.post_processing_tab)
        post_processing_entry.grid(row=1, column=1)

        post_processing_submit_button = Button(self.post_processing_tab, text='Submit',
                                               command=lambda: self.submit_post_processing(contract_id,
                                                                                           post_processing_entry.get()))
        post_processing_submit_button.grid(row=2, column=2)

        # invoice tab
        invoice_label = Label(self.invoice_tab, text='Submit Invoice')
        invoice_label.grid(row=0, column=0, columnspan=3)

        invoice_file_label = Label(self.invoice_tab, text='Choose Invoice File')
        invoice_file_label.grid(row=1, column=0)

        invoice_file_button = Button(self.invoice_tab, text='Browse', command=self.browse)
        invoice_file_button.grid(row=1, column=1)

        invoice_submit_button = Button(self.invoice_tab, text='Submit',
                                       command=lambda: self.submit_invoice(contract_id))
        invoice_submit_button.grid(row=2, column=2)

    def login(self):
        self.user_email = self.email_login.get()
        self.user_pw = self.pw_login.get()
        # try:
        self.user_role = blockchain.login(self.blockchain.cnx, self.user_email)
        if self.user_role is 'undefined':
            messagebox.showerror(message='Account with your email address was not found. Please create an account.')
        else:
            messagebox.showinfo(message='Logged in successfully.')
            self.app_window_setup()
        # except:
        #     messagebox.showerror(message='No local blockchain found.')

    def register_new_user(self, email, pw, role):
        if email is '' or pw is '' or role is '':
            raise AssertionError('You must supply an email, password, and role')
        self.user_email = email
        self.user_pw = pw
        my_role = blockchain.login(self.blockchain.cnx, email)
        if my_role is not 'undefined':
            messagebox.showerror(message='Account with your email address already exists. Please login.')
        else:
            self.blockchain = blockchain.register_user(email, pw, role)
            self.user_role = role.lower()
        self.register_window.quit()

    def register(self):
        self.register_window = Tk()
        self.register_window.title("Register new user")

        welcome_label = Label(self.register_window, text="Please register to create your GPG credentials")
        welcome_label.grid(row=0, column=1)

        new_email_label = Label(self.register_window, text="Email address")
        new_email_label.grid(row=1, column=0)

        new_email_login = Entry(self.register_window)
        new_email_login.grid(row=1, column=1)

        new_pw_label = Label(self.register_window, text="Password")
        new_pw_label.grid(row=2, column=0)

        new_pw_login = Entry(self.register_window)
        new_pw_login.grid(row=2, column=1)

        new_role_label = Label(self.register_window, text="Role")
        new_role_label.grid(row=3, column=0)

        tkvar = StringVar(root)
        tkvar.set('Engineer')
        choices = {'Engineer', 'Technician'}
        role_select = OptionMenu(self.register_window, tkvar, *choices)
        role_select.grid(row=3, column=1)

        role_select_show = Label(self.register_window, text=tkvar.get)
        role_select_show.grid(row=4, column=1)

        register_button = Button(self.register_window, text="Register",
                                 command=lambda: self.register_new_user(new_email_login.get(), new_pw_login.get(),
                                                                        tkvar.get()))
        register_button.grid(row=5, column=1)

        self.register_window.mainloop()


root = Tk()
my_gui = blockchainApp(root, 'windows')
root.mainloop()

# login (email, role, and gpg_pw)
# check if user email is in keyring

# new user page --> generates key, uploads to keyring

# view my projects (get headers)

# open a project by contract id

# within project, place all the process steps, clicking on hash allows you to download it
# similarly, you can execute smart contract functions
