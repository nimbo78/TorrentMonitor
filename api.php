<?php
/**
 * Telegram Bot JSON API
 * All responses: {"error": bool, "msg": string, "data": mixed}
 */
$dir = dirname(__FILE__) . '/';
include_once $dir . 'config.php';
include_once $dir . 'class/Database.class.php';
include_once $dir . 'class/System.class.php';

header('Content-Type: application/json; charset=utf-8');

function api_ok($data = null, $msg = '')
{
    echo json_encode(['error' => false, 'msg' => $msg, 'data' => $data]);
    exit();
}

function api_err($msg)
{
    echo json_encode(['error' => true, 'msg' => $msg, 'data' => null]);
    exit();
}

if ( ! Sys::checkAuth())
    api_err('Unauthorized');

$action = isset($_POST['action']) ? $_POST['action'] : (isset($_GET['action']) ? $_GET['action'] : '');

// --- list ---
if ($action == 'list')
{
    $sort = isset($_POST['sort']) ? $_POST['sort'] : 'date';
    $dir_  = ($sort == 'date') ? 'DESC' : 'ASC';
    $rows = Database::getTorrentsList($sort, $dir_);
    if ( ! $rows) $rows = [];
    $result = [];
    foreach ($rows as $row)
    {
        $result[] = [
            'id'         => (int)$row['id'],
            'name'       => $row['name'],
            'tracker'    => $row['tracker'],
            'torrent_id' => $row['torrent_id'],
            'ep'         => $row['ep'],
            'timestamp'  => $row['timestamp'],
            'pause'      => (int)$row['pause'],
            'type'       => $row['type'],
        ];
    }
    api_ok($result);
}

// --- pause ---
if ($action == 'pause')
{
    $id = (int)$_POST['id'];
    Database::setPause($id, 1);
    api_ok();
}

// --- resume ---
if ($action == 'resume')
{
    $id = (int)$_POST['id'];
    Database::setPause($id, 0);
    api_ok();
}

// --- delete ---
if ($action == 'delete')
{
    $id = (int)$_POST['id'];
    Database::deletItem($id);
    api_ok();
}

// --- add_torrent ---
if ($action == 'add_torrent')
{
    $url = $_POST['url'];
    $name = isset($_POST['name']) ? $_POST['name'] : '';

    $parsed = parse_url($url);
    if ( ! $parsed)
        api_err('Неверный URL');

    $tracker = preg_replace('/^www\./', '', $parsed['host']);

    if (in_array($tracker, ['lostfilm.tv', 'lostfilm-mirror', 'newstudio.tv']))
        api_err('Это не форумный трекер. Добавьте как Сериал.');

    if ($tracker == 'tr.anidub.com') $tracker = 'anidub.com';
    elseif ($tracker == 'baibako.tv') $tracker = 'baibako.tv_forum';

    if ($tracker == 'anidub.com' || $tracker == 'riperam.org')
        $threme = $parsed['path'];
    elseif ($tracker == 'animelayer.ru')
    {
        $path = str_replace('/torrent', '', $parsed['path']);
        preg_match('/\/(\w*)\/?' , $path, $array);
        $threme = $array[1];
    }
    elseif ($tracker == 'casstudio.tk')
    {
        $q = explode('t=', $parsed['query']);
        $threme = $q[1];
    }
    elseif ($tracker != 'rutor.is')
    {
        $q = explode('=', $parsed['query']);
        $threme = $q[1];
    }
    else
    {
        preg_match('/\d{4,8}/', $parsed['path'], $array);
        $threme = $array[0];
    }

    if (empty($threme))
        api_err('Не удалось определить ID темы из URL');

    if ( ! is_array(Database::getCredentials($tracker)))
        api_err('Нет учётных данных для трекера: ' . $tracker);

    $engineFile = $dir . 'trackers/' . $tracker . '.engine.php';
    if ( ! file_exists($engineFile))
        api_err('Нет модуля для трекера: ' . $tracker);

    include_once $engineFile;
    $class = str_replace('-', '', explode('.', $tracker)[0]);
    if ($tracker == 'tracker.0day.kiev.ua') $class = 'kiev';
    if ($tracker == 'tv.mekc.info')         $class = 'mekc';
    if ($tracker == 'baibako.tv_forum')     $class = 'baibako_f';

    if ( ! call_user_func([$class, 'checkRule'], $threme))
        api_err('Тема не прошла проверку трекера');

    if ( ! Database::checkThremExist($tracker, $threme))
        api_err('Тема уже добавлена');

    if (empty($name))
        $name = Sys::getHeader($url);

    $query = Database::setThreme($tracker, $name, '', $threme, 0);
    if ($query === TRUE)
        api_ok(null, 'Тема добавлена для мониторинга.');
    else
        api_err('Ошибка при сохранении в БД');
}

// --- add_serial ---
if ($action == 'add_serial')
{
    $tracker = $_POST['tracker'];
    $name    = $_POST['name'];
    $hd      = isset($_POST['hd']) ? (int)$_POST['hd'] : 0;

    if ( ! is_array(Database::getCredentials($tracker)))
        api_err('Нет учётных данных для трекера: ' . $tracker);

    $engineFile = $dir . 'trackers/' . $tracker . '.engine.php';
    if ( ! file_exists($engineFile))
        api_err('Нет модуля для трекера: ' . $tracker);

    include_once $engineFile;

    if ( ! Database::checkSerialExist($tracker, $name, $hd))
        api_err('Сериал уже добавлен для этого трекера');

    $query = Database::setSerial($tracker, $name, '', $hd);
    if ($query === TRUE)
        api_ok(null, 'Сериал добавлен для мониторинга.');
    else
        api_err('Ошибка при сохранении в БД');
}

// --- get_warnings ---
if ($action == 'get_warnings')
{
    $trackers = Database::getWarningsCount();
    if ( ! $trackers) $trackers = [];
    $result = [];
    foreach ($trackers as $t)
    {
        $warnings = Database::getWarningsList($t['where']);
        if ( ! $warnings) continue;
        foreach ($warnings as $w)
        {
            $result[] = [
                'time'     => $w['time'],
                'location' => $w['where'],
                'reason'   => $w['reason'],
            ];
        }
    }
    api_ok($result);
}

// --- get_credentials ---
if ($action == 'get_credentials')
{
    $creds = Database::getAllCredentials();
    if ( ! $creds) $creds = [];
    $result = [];
    foreach ($creds as $c)
    {
        $result[] = [
            'id'          => (int)$c['id'],
            'tracker'     => $c['tracker'],
            'log'         => $c['login'],
            'necessarily' => (int)$c['necessarily'],
        ];
    }
    api_ok($result);
}

// --- set_credentials ---
if ($action == 'set_credentials')
{
    $id      = (int)$_POST['id'];
    $log     = $_POST['log'];
    $pass    = $_POST['pass'];
    $passkey = isset($_POST['passkey']) ? $_POST['passkey'] : '';
    Database::setCredentials($id, $log, $pass, $passkey);
    api_ok();
}

// --- get_settings ---
if ($action == 'get_settings')
{
    $rows = Database::getAllSetting();
    if ( ! $rows) $rows = [];
    $result = [];
    foreach ($rows as $row)
    {
        foreach ($row as $k => $v)
            $result[$k] = $v;
    }
    // никогда не возвращаем пароль
    unset($result['password']);
    api_ok($result);
}

// --- update_setting ---
if ($action == 'update_setting')
{
    $key = $_POST['key'];
    $val = $_POST['val'];
    if ($key == 'password')
        api_err('Обновление пароля через этот endpoint запрещено');
    Database::updateSettings($key, $val);
    api_ok();
}

// --- get_new_items ---
if ($action == 'get_new_items')
{
    $since = $_POST['since'];
    $stmt = Database::getInstance()->dbh->prepare(
        "SELECT t.id, t.tracker, t.name, t.torrent_id, t.ep, t.timestamp, t.pause,
                COALESCE(c.type, '') AS type
         FROM torrent t
         LEFT JOIN credentials c ON c.tracker = t.tracker
         WHERE t.timestamp > :since
         ORDER BY t.timestamp DESC"
    );
    $stmt->bindParam(':since', $since);
    $result = [];
    if ($stmt->execute())
    {
        foreach ($stmt as $row)
        {
            $result[] = [
                'id'         => (int)$row['id'],
                'name'       => $row['name'],
                'tracker'    => $row['tracker'],
                'torrent_id' => $row['torrent_id'],
                'ep'         => $row['ep'],
                'timestamp'  => $row['timestamp'],
                'pause'      => (int)$row['pause'],
                'type'       => $row['type'],
            ];
        }
    }
    api_ok($result);
}

api_err('Неизвестный action: ' . $action);
