<?php
// Project configuration; the installer above supplies database and secret keys.
$wgSitename = 'Dungeon Crawl — русская вики';
$wgMetaNamespace = 'Dungeon_Crawl';
$wgLanguageCode = 'ru';
$wgLocaltimezone = 'Europe/Moscow';
$wgArticlePath = '/wiki/$1';
$wgUsePathInfo = true;
$wgDefaultSkin = 'vector';
$wgVectorDefaultSkinVersion = '1';
$wgVectorResponsive = true;
$wgEnableUploads = true;
$wgFileExtensions = [ 'png', 'jpg', 'jpeg', 'webp', 'gif' ];
$wgUploadPath = '/images';
$wgUploadDirectory = '/srv/dcss-wiki/shared/images';
$wgTmpDirectory = '/srv/dcss-wiki/shared/cache';
$wgCacheDirectory = '/srv/dcss-wiki/shared/cache';
$wgUseImageMagick = false;
$wgUseInstantCommons = false;
// CLI content updates and FPM must share invalidation state.
$wgMainCacheType = CACHE_DB;
$wgJobRunRate = 0.1;
$wgArticleCountMethod = 'any';
$wgCookieSecure = true;
$wgCookiePrefix = 'dcsswiki';
$wgGroupPermissions['*']['read'] = true;
$wgGroupPermissions['*']['edit'] = false;
$wgGroupPermissions['*']['createaccount'] = false;
$wgGroupPermissions['user']['edit'] = true;
$wgGroupPermissions['user']['upload'] = true;
$wgGroupPermissions['sysop']['createaccount'] = true;
$wgEnableEmail = false;
$wgEnableUserEmail = false;
$wgEmergencyContact = '';
$wgPasswordSender = '';
$wgPingback = false;
$wgLogos = [ '1x' => '/resources/dcss/wiki-logo.svg', 'icon' => '/resources/dcss/favicon.png' ];
$wgHooks['BeforePageDisplay'][] = static function ( $out, $skin ) {
    $theme = '/srv/dcss-wiki/shared/resources/theme.css';
    if ( is_file( $theme ) ) {
        $out->addLink( [ 'rel' => 'stylesheet',
            'href' => '/resources/dcss/theme.css?v=' . substr( hash_file( 'sha256', $theme ), 0, 12 ) ] );
    }
};
$wgHooks['ShowSearchHit'][] = static function ( $searchPage, $result, $terms, &$link,
    &$redirect, &$section, &$extract, &$score, &$size, &$date, &$related, &$html ) {
    static $summaries = null;
    if ( $summaries === null ) {
        $path = '/srv/dcss-wiki/shared/search-extracts.json';
        $summaries = is_file( $path ) ? json_decode( file_get_contents( $path ), true ) : [];
    }
    $title = $result->getTitle();
    if ( $title && isset( $summaries[$title->getPrefixedText()] ) ) {
        $extract = '<div class="searchresult">' . htmlspecialchars( $summaries[$title->getPrefixedText()], ENT_QUOTES | ENT_SUBSTITUTE, 'UTF-8' ) . '</div>';
    }
};
$wgRightsText = 'GNU FDL; условия файлов указаны на их страницах';
$wgRightsUrl = 'https://www.gnu.org/licenses/fdl.html';
$wgRightsIcon = '';
wfLoadExtension( 'ParserFunctions' );
wfLoadExtension( 'Cite' );
wfLoadExtension( 'InputBox' );

// DCSS-NAVIGATION-RUNTIME-BEGIN
$wgHooks['OutputPageAfterGetHeadLinksArray'][] = static function ( &$tags, $out ) {
    // Legacy Vector forces a desktop viewport even with project mobile CSS.
    $tags['meta-viewport'] = '<meta name="viewport" content="width=device-width, initial-scale=1">';
};
$wgHooks['BeforePageDisplay'][] = static function ( $out, $skin ) {
    $script = '/srv/dcss-wiki/shared/resources/navigation.js';
    if ( is_file( $script ) ) {
        $url = '/resources/dcss/navigation.js?v=' . substr( hash_file( 'sha256', $script ), 0, 12 );
        $out->addHeadItem( 'dcss-directory-filter', '<script defer src="' . $url . '"></script>' );
    }
};
// DCSS-NAVIGATION-RUNTIME-END
