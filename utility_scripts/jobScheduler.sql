DO $$
DECLARE
    jid integer;
    scid integer;
BEGIN
-- Creating a new job
INSERT INTO pgagent.pga_job(
    jobjclid, jobname, jobdesc, jobhostagent, jobenabled
) VALUES (
    1::integer, 'DBUpdateScript'::text, ''::text, ''::text, true
) RETURNING jobid INTO jid;

-- Steps
-- Inserting a step (jobid: NULL)
INSERT INTO pgagent.pga_jobstep (
    jstjobid, jstname, jstenabled, jstkind,
    jstconnstr, jstdbname, jstonerror,
    jstcode, jstdesc
) VALUES (
    jid, 'runBatch'::text, true, 'b'::character(1),
    ''::text, ''::name, 'f'::character(1),
    ':: ###############################################################
:: ############# BATCH SCRIPT FOR JOB RUNNER #####################
:: ###############################################################

:: FIND DBUPDATESCRIPT.PY
cd "%~dp0..\src"

:: RUN SCRIPT
python DBUpdateScript.py %*
PAUSE'::text, ''::text
) ;

-- Schedules
-- Inserting a schedule
INSERT INTO pgagent.pga_schedule(
    jscjobid, jscname, jscdesc, jscenabled,
    jscstart, jscend,    jscminutes, jschours, jscweekdays, jscmonthdays, jscmonths
) VALUES (
    jid, 'bi_monthly'::text, ''::text, true,
    '2021-07-02T10:00:16-04:00'::timestamp with time zone, '2022-12-02T09:57:35-05:00'::timestamp with time zone,
    -- Minutes
    ARRAY[false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false]::boolean[],
    -- Hours
    ARRAY[false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false]::boolean[],
    -- Week days
    ARRAY[false,false,false,false,false,false,false]::boolean[],
    -- Month days
    ARRAY[false,true,false,false,false,false,false,false,false,false,false,false,false,false,true,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false,false]::boolean[],
    -- Months
    ARRAY[false,false,false,false,false,false,false,false,false,false,false,false]::boolean[]
) RETURNING jscid INTO scid;
END
$$;