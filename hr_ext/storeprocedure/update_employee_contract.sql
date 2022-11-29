-- Function: update_employee_contract()
-- select * from update_employee_contract()
-- DROP FUNCTION update_employee_contract()

CREATE OR REPLACE FUNCTION update_employee_contract()
  RETURNS void AS
$BODY$
DECLARE
	emp record;
	emp_contract integer;
BEGIN
	
	for emp in select id from hr_employee where active=true and contract_id is null
	loop
		RAISE NOTICE 'Calling emp(%)', emp;
		select id into emp_contract from hr_contract where state='open' and employee_id=emp.id;
		RAISE NOTICE 'Calling emp_contract(%)', emp_contract;
		update hr_employee set contract_id=emp_contract where id=emp.id;
	end loop;
		

END;
$BODY$
  LANGUAGE plpgsql VOLATILE
  COST 100; 