import json
import pdfplumber
import re

from bs4 import BeautifulSoup
from dateutil.parser import parse as str_to_date
from hashlib import sha256




class PDFExtractor:
    def __init__(self, filename):
        self.filename = filename
        self.sections_list = [
            '\nPAST MEDICAL HISTORY:',
            '\nPAST SURGICAL HISTORY:',
            '\nFAMILY HISTORY:',
            '\nPhysician:',
            '\nMedical Asst:',
            '\nVisit Date:',
            'Patient:',
            'Date Of Birth:',
            '\nService Location:',
            '\nSOCIAL HISTORY/HABITS:',
            '\nMASTER MEDICATIONS:',
            '\nMASTER PROBLEM LIST',
            '\nASSESSMENT/IMPRESSION:',
            '\nPROCEDURES PERFORMED:',
            '\nFollow-up Visit:',
        ]
        self.pdf_text = self.clean_data(self.read_data())
        self.html_text = self.read_html()

    def read_html(self):
        filename = self.filename.replace('_doc_1.pdf', '_contact.html')
        with open(filename) as html:
            html = html.read()
        data = BeautifulSoup(html, 'html.parser')
        return data

    def read_data(self):
        pdf_text = ''
        with pdfplumber.open(self.filename) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                pdf_text += page_text + '\n'
        return pdf_text

    def clean_data(self, pdf_text):
        footer_pattern = r'\n[\w\s]+\d+/\d+/\d{4}[(Male|Female)\s]+ Visit Date:[\w\s\d\n]+Page[\w\s]+\n'
        footer = re.sub(footer_pattern, '\n', pdf_text)
        pdf_text = re.sub(r'\nSigned:[\s_]+[\w\s,]+#\d+\n', '\n', footer).replace('\u2010', '-')
        return pdf_text

    def get_section_data(self, sec_title):
        section_data = self.pdf_text.split(sec_title)[-1]
        for sec in self.sections_list:
            if sec in section_data:
                section_data = section_data.split(sec)[0]
        return section_data.strip()

    def get_medical_history(self):
        sec_title = '\nPAST MEDICAL HISTORY:'
        medical_history = self.get_section_data(sec_title).split('\n')
        return medical_history

    def get_surgical_history(self):
        sec_title = '\nPAST SURGICAL HISTORY:'
        surgical_history = self.get_section_data(sec_title)
        return surgical_history

    def get_family_history(self):
        sec_title = '\nFAMILY HISTORY:'
        family_history = self.get_section_data(sec_title)
        return family_history

    def get_physician(self):
        sec_title = '\nPhysician:'
        physician = self.get_section_data(sec_title)
        return physician

    def get_medical_asst(self):
        sec_title = '\nMedical Asst:'
        medical_asst = self.get_section_data(sec_title)
        return medical_asst

    def get_visit_date(self):
        sec_title = '\nVisit Date:'
        visit_date = re.findall(r'[\w\s]+\d{4}', self.get_section_data(sec_title))
        return visit_date

    def get_patient(self):
        sec_title = 'Patient:'
        patient = self.get_section_data(sec_title)
        return patient

    def get_dob(self):
        sec_title = 'Date Of Birth:'
        dob = [self.get_section_data(sec_title)]
        print(dob)
        if len(set(dob)) != 1:
            raise Exception(f"DOB not found: {set(dob)}")
        return dob

    def get_service_location(self):
        sec_title = '\nService Location:'
        service_location = self.get_section_data(sec_title)
        return service_location

    def get_social_history(self):
        sec_title = '\nSOCIAL HISTORY/HABITS:'
        social_history = self.get_section_data(sec_title)
        return social_history

    def get_master_medication(self):
        sec_title = '\nMASTER MEDICATIONS:'
        master_medication = self.get_section_data(sec_title)
        return master_medication

    def get_master_problem(self):
        sec_title = '\nMASTER PROBLEM LIST'
        master_problem_list = []
        master_problem = re.sub(r'\([\w\s]+\):', '', self.get_section_data(sec_title)).split('\n')
        master_problem = [item for item in master_problem if item]
        master_problem = [item.split(maxsplit=1)[-1] for item in master_problem if isinstance(item, str)]
        for problem in master_problem:
            code = problem.split('-')[0].strip()
            description = problem.split('-')[-1].strip()
            master_problem_list.append({
                        'code': code,
                        'description': description
                    })
        return master_problem_list

    def get_assessment(self):
        sec_title = '\nASSESSMENT/IMPRESSION:'
        assessment = re.sub(r'[\w\s]+:', '', self.get_section_data(sec_title))
        assessment = assessment.split(maxsplit = 1)[-1]

        return assessment

    def get_procedures_performed(self):
        sec_title = '\nPROCEDURES PERFORMED:'
        procedures_performed = self.get_section_data(sec_title)
        return procedures_performed

    def get_followup_visit(self):
        sec_title = '\nFollow-up Visit:'
        followup_visit = self.get_section_data(sec_title)
        return followup_visit
    
    def create_patient_id(self):
        given_name = self.get_patient().split(maxsplit=1)[0]
        family_name = self.get_patient().split(maxsplit=1)[-1]
        dob = self.get_dob()
        patient_id = given_name + family_name + dob[0]
        patient_id = re.sub(r'[^\w\d]+', '', patient_id.lower())
        patient_id = sha256(patient_id.encode('utf-8')).hexdigest()
        return patient_id
    
    def get_primary_info(self):
        table_tr = self.html_text.find('div', attrs={'id': 'div_show'}).find('table').find('tr', attrs = {'id': 'tr_clinic'})
        headers = [header.get_text(strip=True) for header in  table_tr.find_all('tr')[0].find_all('td')]
        values = [value.get_text(strip=True) for value in  table_tr.find_all('tr')[1].find_all('span')]
        primary_info = dict(zip(headers, values))
        return primary_info
    
    def get_personal_info(self):
        table_tr = self.html_text.select_one("#div_show > table > tbody > tr:nth-of-type(3) > td > table > tbody")
        personal_info = self.get_details(table_tr)
        return personal_info
    
    def get_contact_info(self):
        table_tr = self.html_text.select_one("#div_show > table > tbody > tr:nth-of-type(4) > td > table > tbody")
        contact_info = self.get_details(table_tr)
        return contact_info
    
    def get_emergency_info(self):
        table_tr = self.html_text.select_one("#div_show > table > tbody > tr:nth-of-type(6) > td > table > tbody")
        emergency_info = self.get_details(table_tr)
        return emergency_info
    
    def get_details(self, table_tr):
        headers = [td.get_text(strip=True) for td in table_tr.select('td[style*="font-weight: bold"]')]
        values = [td.get_text(strip=True) for td in table_tr.select('td:not([style*="font-weight: bold"]) span')]
        details = dict(zip(headers, values))
        return details
    
    def get_clinical_info(self):
        table_tr = self.html_text.select_one("#div_clinic_add > table > tbody")
        clinical_info = [td.get_text(strip=True) for td in table_tr.select('tr > td') if not td.find('table') and td.get_text(strip=True) != '']
        return clinical_info

    def generate_output(self):
        date = str_to_date(self.get_visit_date()[0].strip()).strftime("%m/%d/%Y")
        data = {}
        data["medical_history"] = {}
        data["surgical_history"] = {}
        data["family_history"] ={}
        data["physician"] = {}
        data["patient"] = {}
        data["social_history"] = {}
        data["master_medication"] = {}
        data["master_problem"] = {}
        data["assessments"] = {}
        data["procedures_performed"] = {}

        data["encdate"] = date
        data["medical_history"]['history'] = self.get_medical_history()
        data["medical_history"]['date'] = date
        data["surgical_history"]['description'] = self.get_surgical_history()
        data["surgical_history"]['date'] = date
        data["family_history"]['description'] = self.get_family_history()
        data["family_history"]['date'] = date
        data["physician"]['given'] = self.get_physician().split(maxsplit=1)[0]
        data["physician"]['family'] = self.get_physician().split(maxsplit=1)[-1]
        data['patient_id'] = self.create_patient_id()
        data["medical_asst"] = self.get_medical_asst()
        data["visit_date"] = str_to_date(self.get_visit_date()[0].strip()).strftime("%m/%d/%Y")
        data["patient"]['given'] = self.get_patient().split(maxsplit=1)[0]
        data["patient"]['family'] = self.get_patient().split(maxsplit=1)[-1].split('-')[0].strip()
        data["patient"]["dob"] = str_to_date(self.get_dob()[0].strip()).strftime("%m/%d/%Y")
        data["service_location"] = self.get_service_location()
        data["social_history"]['description'] = self.get_social_history()
        data["social_history"]['date'] = date
        data["master_medication"]["medication"] = self.get_master_medication().split(':')[-1].replace('\n', ' ').split(',')[0].strip()
        data["master_medication"]["instruction"] = self.get_master_medication().split(':')[-1].replace('\n', ' ').split(',')[-1].strip()
        data["master_medication"]['date'] = date
        data["master_medication"]['status'] = self.get_master_medication().split(':')[0].strip()
        data["master_problem"] = self.get_master_problem()
        data["assessments"]["code"] = self.get_assessment().split('-')[0].strip()
        data["assessments"]["assessment"] = self.get_assessment().split('-')[-1].strip()
        data["assessments"]['date'] = date
        data["procedures_performed"]['description'] = self.get_procedures_performed()
        data["procedures_performed"]['date'] = date
        data["followup_visit"] = self.get_followup_visit()
        data['primary_info'] = self.get_primary_info()
        data['personal_info'] = self.get_personal_info()
        data['contact_info'] = self.get_contact_info()
        data['emergency_info'] = self.get_emergency_info()
        data['clinical_info'] = self.get_clinical_info()

        output_filename = self.filename.replace('.pdf', '.json')
        with open(output_filename, 'w') as json_file:
            json.dump(data, json_file, indent=4)
        return data

extractor = PDFExtractor('1000017_doc_1.pdf')
json_output = extractor.generate_output()
print(json_output)
